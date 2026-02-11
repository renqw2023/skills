"""
Marker PDF OCR Service - Core Implementation
Local-first deployment with cloud fallback
"""
import os
import json
import subprocess
import tempfile
import time
import requests
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass


class DeploymentMode(Enum):
    AUTO = "auto"
    LOCAL = "local"
    CLOUD = "cloud"


@dataclass
class ConversionResult:
    content: str
    format: str
    mode_used: str
    pages: int
    processing_time: float
    metadata: Optional[Dict[str, Any]] = None


class MarkerOCRService:
    """Main service for PDF OCR conversion"""
    
    # Datalab.to API endpoints
    CLOUD_API_BASE = "https://www.datalab.to/api/v1"
    
    def __init__(self):
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment"""
        return {
            "api_key": os.getenv("MARKER_API_KEY"),
            "default_mode": os.getenv("MARKER_DEPLOYMENT_MODE", "auto"),
            "max_memory_mb": int(os.getenv("MARKER_MAX_MEMORY_MB", "4096")),
            "timeout": int(os.getenv("MARKER_TIMEOUT_SECONDS", "300"))
        }
    
    def convert(self, pdf_path: str, mode: str = "auto",
                output_format: str = "markdown",
                timeout: Optional[int] = None) -> ConversionResult:
        """
        Convert PDF to target format
        
        Args:
            pdf_path: Path to input PDF
            mode: auto/local/cloud
            output_format: markdown/json/html
            timeout: Processing timeout
        
        Returns:
            ConversionResult with content and metadata
        """
        # Validate input file
        self._validate_pdf(pdf_path)
        
        # Resolve mode
        if mode == "auto":
            mode = self._select_best_mode()
        
        # Route to appropriate handler
        timeout = timeout or self.config["timeout"]
        
        if mode == "local":
            return self._convert_local(pdf_path, output_format, timeout)
        else:
            return self._convert_cloud(pdf_path, output_format, timeout)
    
    def _validate_pdf(self, pdf_path: str) -> None:
        """Validate PDF file before processing"""
        path = Path(pdf_path)
        
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {pdf_path}")
        
        # Check extension
        if path.suffix.lower() != '.pdf':
            raise ValueError(f"File must be PDF, got: {path.suffix}")
        
        # Check size (100MB limit)
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 100:
            raise ValueError(f"PDF too large: {size_mb:.1f}MB (max 100MB)")
    
    def _select_best_mode(self) -> str:
        """Auto-select best mode based on environment"""
        # Check if local marker is available
        if self._is_local_available():
            # Check memory
            free_memory = self._get_free_memory_mb()
            if free_memory >= 2048:  # Relaxed to 2GB with swap
                return "local"
        
        # Fall back to cloud if API key available
        if self.config["api_key"]:
            return "cloud"
        
        # No viable mode
        raise RuntimeError(
            "No viable deployment mode. Either install marker-pdf locally "
            "or set MARKER_API_KEY for cloud mode."
        )
    
    def _is_local_available(self) -> bool:
        """Check if marker-pdf is installed locally"""
        try:
            result = subprocess.run(
                ["python3", "-c", "import marker; print('ok')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and "ok" in result.stdout
        except:
            return False
    
    def _get_free_memory_mb(self) -> int:
        """Get available system memory (including swap)"""
        try:
            # Read both MemAvailable and SwapFree
            mem_available = 0
            swap_free = 0
            
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        mem_available = int(line.split()[1]) // 1024
                    elif line.startswith('SwapFree:'):
                        swap_free = int(line.split()[1]) // 1024
            
            # With 23GB swap, we can use swap as effective memory
            return mem_available + swap_free
        except:
            return 0
    
    def _convert_local(self, pdf_path: str, output_format: str,
                      timeout: int) -> ConversionResult:
        """Convert using local marker-pdf via subprocess CLI"""
        start = time.time()
        
        pdf_file = Path(pdf_path)
        output_dir = tempfile.mkdtemp(prefix="marker_output_")
        
        try:
            # Use the correct CLI command
            cmd = [
                "python3", "-m", "marker.scripts.convert_single",
                str(pdf_file),
                "--output_dir", output_dir
            ]
            
            # Run conversion with proper env
            env = os.environ.copy()
            env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            # Check for errors in stderr
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                raise RuntimeError(f"Marker conversion failed: {error_msg}")
            
            # marker saves to a folder with the PDF name
            pdf_name = pdf_file.stem
            expected_output_dir = Path(output_dir) / pdf_name
            
            # Find output file
            output_files = []
            search_dirs = [Path(output_dir), expected_output_dir]
            
            for search_dir in search_dirs:
                if search_dir.exists():
                    output_files.extend(list(search_dir.glob("*.md")))
                    output_files.extend(list(search_dir.glob("*.json")))
                    output_files.extend(list(search_dir.glob("*.txt")))
            
            if not output_files:
                # List what was created for debugging
                created = list(Path(output_dir).rglob("*"))
                raise RuntimeError(f"No output file generated. Created: {created}")
            
            # Read output
            output_file = output_files[0]
            content = output_file.read_text(encoding='utf-8')
            
            # Count pages (rough estimate)
            pages = content.count('\n\n') // 20 + 1
            
            processing_time = time.time() - start
            
            return ConversionResult(
                content=content,
                format=output_format,
                mode_used="local",
                pages=pages,
                processing_time=processing_time,
                metadata={"output_file": str(output_file)}
            )
            
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Local conversion timed out after {timeout}s")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Marker process failed: {e.stderr}")
        except MemoryError:
            raise MemoryError(
                "Local mode ran out of memory. "
                "Try --mode cloud or increase MARKER_MAX_MEMORY_MB"
            )
        finally:
            # Cleanup temp directory
            import shutil
            try:
                shutil.rmtree(output_dir, ignore_errors=True)
            except:
                pass
    
    def _convert_cloud(self, pdf_path: str, output_format: str,
                      timeout: int) -> ConversionResult:
        """Convert using Datalab.to API"""
        start = time.time()
        
        api_key = self.config.get("api_key")
        if not api_key:
            raise RuntimeError("MARKER_API_KEY not set for cloud mode")
        
        pdf_file = Path(pdf_path)
        
        try:
            # Step 1: Upload PDF and start conversion
            with open(pdf_file, 'rb') as f:
                files = {'file': (pdf_file.name, f, 'application/pdf')}
                data = {
                    'output_format': output_format,
                    'force_cpu': 'true'  # Consistent with local mode
                }
                headers = {'X-API-Key': api_key}
                
                response = requests.post(
                    f"{self.CLOUD_API_BASE}/convert",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )
            
            if response.status_code != 200:
                error_msg = f"API error {response.status_code}: {response.text}"
                if response.status_code == 429:
                    raise RuntimeError(f"API rate limit exceeded. {error_msg}")
                elif response.status_code == 401:
                    raise RuntimeError(f"Invalid API key. {error_msg}")
                else:
                    raise RuntimeError(error_msg)
            
            result = response.json()
            
            # Step 2: Poll for completion (if async)
            if result.get('status') == 'pending':
                request_id = result.get('request_id')
                content = self._poll_cloud_result(request_id, api_key, timeout)
            else:
                content = result.get('markdown', result.get('content', ''))
            
            processing_time = time.time() - start
            
            return ConversionResult(
                content=content,
                format=output_format,
                mode_used="cloud",
                pages=result.get('page_count', 0),
                processing_time=processing_time,
                metadata={"api_response": result}
            )
            
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Cloud API request timed out")
        except requests.exceptions.ConnectionError:
            raise ConnectionError("Cannot connect to Datalab API. Check internet.")
    
    def _poll_cloud_result(self, request_id: str, api_key: str,
                          timeout: int) -> str:
        """Poll for cloud conversion result"""
        import time
        
        start_time = time.time()
        poll_interval = 2  # Start with 2 seconds
        
        while time.time() - start_time < timeout:
            response = requests.get(
                f"{self.CLOUD_API_BASE}/result/{request_id}",
                headers={'X-API-Key': api_key},
                timeout=30
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Poll failed: {response.text}")
            
            result = response.json()
            
            if result.get('status') == 'completed':
                return result.get('markdown', result.get('content', ''))
            elif result.get('status') == 'failed':
                raise RuntimeError(f"Conversion failed: {result.get('error', 'Unknown')}")
            
            # Exponential backoff (max 10 seconds)
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 10)
        
        raise TimeoutError("Cloud conversion timed out waiting for result")
    
    def health_check(self) -> Dict[str, Any]:
        """Check system health and available modes"""
        result = {
            "healthy": False,
            "available_modes": [],
            "recommended_mode": "unknown",
            "local_ready": False,
            "cloud_ready": False,
            "memory_available_mb": 0,
            "version": "1.0.0"
        }
        
        # Check memory
        result["memory_available_mb"] = self._get_free_memory_mb()
        
        # Check local availability
        result["local_ready"] = self._is_local_available()
        if result["local_ready"]:
            result["available_modes"].append("local")
        
        # Check cloud availability
        result["cloud_ready"] = bool(self.config.get("api_key"))
        if result["cloud_ready"]:
            result["available_modes"].append("cloud")
        
        # Determine recommended mode
        # With 23GB swap, local is almost always viable
        if result["local_ready"]:
            result["recommended_mode"] = "local"
        elif result["cloud_ready"]:
            result["recommended_mode"] = "cloud"
        
        # Overall health
        result["healthy"] = len(result["available_modes"]) > 0
        
        return result
    
    def install_local(self) -> bool:
        """Install marker-pdf locally"""
        try:
            # Install marker-pdf with CPU-only torch
            cmd = [
                "pip", "install", "-q",
                "marker-pdf",
                "torch",
                "--extra-index-url", "https://download.pytorch.org/whl/cpu"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            return result.returncode == 0
        except Exception as e:
            print(f"Installation failed: {e}")
            return False


# Error classification for retry logic
class ErrorClassification:
    """Classify errors for appropriate handling"""
    
    RETRYABLE_TRANSIENT = ["TimeoutError", "ConnectionError"]
    RETRYABLE_WITH_BACKOFF = ["APIQuotaExceeded", "RateLimitError"]
    NOT_RETRYABLE = ["FileNotFoundError", "PermissionError", "ValueError"]
    REQUIRES_MODE_SWITCH = ["MemoryError", "APIQuotaExceeded"]
    
    @classmethod
    def classify(cls, error: Exception) -> str:
        """Classify an error"""
        error_type = type(error).__name__
        
        if error_type in cls.RETRYABLE_TRANSIENT:
            return "retryable_transient"
        elif error_type in cls.RETRYABLE_WITH_BACKOFF:
            return "retryable_backoff"
        elif error_type in cls.NOT_RETRYABLE:
            return "not_retryable"
        elif error_type in cls.REQUIRES_MODE_SWITCH:
            return "mode_switch"
        else:
            return "unknown"
