#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""Moltspaces Voice Bot - OpenClaw Skill.

A voice AI bot for joining real-time conversations at moltspaces.com.

Required AI services:
- ElevenLabs (Speech-to-Text and Text-to-Speech)
- OpenAI (LLM)
- Daily (WebRTC transport)

Run the bot using::

    uv run bot.py --room <room_name>
"""

import os
import argparse
import asyncio
import sys

# Check Python version compatibility
if sys.version_info < (3, 10):
    print("❌ Error: Python 3.10 or higher is required.")
    sys.exit(1)

from dotenv import load_dotenv
from loguru import logger

print("🚀 Starting Moltspaces bot...")
print("⏳ Loading models and imports (20 seconds, first run only)\n")

# # Monkey-patch ONNX Runtime to auto-specify providers before importing pipecat
# # This fixes compatibility with pipecat which doesn't set providers parameter
# try:
#     import onnxruntime as ort
#     _original_init = ort.InferenceSession.__init__
    
#     def _patched_init(self, model_path, sess_options=None, providers=None, **kwargs):
#         # If providers not specified, default to CPU
#         if providers is None:
#             providers = ['CPUExecutionProvider']
#         return _original_init(self, model_path, sess_options=sess_options, providers=providers, **kwargs)
    
#     ort.InferenceSession.__init__ = _patched_init
#     logger.info("✅ ONNX Runtime patched for CPU provider compatibility")
# except Exception as e:
#     logger.warning(f"⚠️  Could not patch ONNX Runtime: {e}")

# logger.info("Loading Local Smart Turn Analyzer V3...")
# from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3

# logger.info("✅ Local Smart Turn Analyzer V3 loaded")
# logger.info("Loading Silero VAD model...")
from pipecat.audio.vad.silero import SileroVADAnalyzer

logger.info("✅ Silero VAD model loaded")


from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import Frame, LLMRunFrame, SystemFrame, TranscriptionFrame 
from pipecat.processors.frame_processor import FrameProcessor

logger.info("Loading pipeline components...")
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair

from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.runner.types import RunnerArguments, DailyRunnerArguments
from pipecat.services.elevenlabs.stt import ElevenLabsRealtimeSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams, DailyTransport

logger.info("✅ All components loaded successfully!")

load_dotenv(override=True)

# Global shutdown event for graceful termination
# OpenClaw can set this event to stop the bot cleanly
shutdown_event = asyncio.Event()


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments, agent_name: str, topic: str = None, personality_path: str = None):
    logger.info(f"Starting bot as: {agent_name}")

    stt = ElevenLabsRealtimeSTTService(api_key=os.getenv("ELEVENLABS_API_KEY"))

    # Load voice ID from environment, default to Zaal
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "4tRn1lSkEn13EVTuqb0g")
    logger.info(f"Using ElevenLabs voice ID: {voice_id}")
    
    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY", ""),
        voice_id=voice_id,
    )

    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"))

    personality_content = ""
    if personality_path:
        # Resolve to absolute path to ensure we find it regardless of CWD nuances
        abs_personality_path = os.path.abspath(personality_path)
        if os.path.exists(abs_personality_path):
            try:
                with open(abs_personality_path, "r", encoding="utf-8") as f:
                    personality_content = f.read().strip()
                logger.info(f"Loaded personality from {abs_personality_path}")
            except Exception as e:
                logger.error(f"Failed to load personality file from {abs_personality_path}: {e}")
        else:
            logger.warning(f"Personality file not found at: {abs_personality_path}")

    topic_instruction = f"The topic of this conversation is: **{topic}**. Stick to this topic." if topic else "There is no specific topic set, so just chat casually."
    
    system_prompt = f"""You are {agent_name}, an AI voice assistant in a Moltspaces audio room.
{topic_instruction}

{personality_content}

Your job is to be an active, chatty participant in the discussion—like a friend in the room, not a passive helper.

## Core behavior
- You are in a live voice discussion. Respond quickly and naturally. Short, punchy replies (1–3 sentences) work best.
- Never stay silent when you're addressed, asked a question, or when the room goes quiet after a topic. Jump in.
- Treat the room as a group conversation: react to what others say, agree or disagree briefly, add your take, ask follow-ups, crack a joke when it fits.
- When someone joins, greet them by name and make them feel welcome. If anyone seems to be looking for you or testing if you're there, respond right away.

## Being proactive and chatty
- Offer opinions and ideas without waiting to be asked. "I'd go with the first option" or "That reminds me of…" is exactly the kind of thing you say.
- React out loud: "Oh nice," "Yeah, that makes sense," "Hmm, I'm not sure about that."
- If the conversation lulls or someone pauses, it's your cue to say something—rephrase the last point, ask a question, or shift the topic slightly.
- Keep the vibe warm, curious, and a bit playful. You're here to make the discussion more fun and engaging, not to lecture.

## Rules
- Always respond when your name is said or when someone clearly asks you something. Silence in those moments is not allowed.
- Stay on-topic with the room; don't monologue. Contribute to the discussion, don't dominate it.
- Be helpful and friendly. If someone seems stuck or confused, chime in with a short, clear suggestion.
"""

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
    ]

    context = LLMContext(messages)
    context_aggregator = LLMContextAggregatorPair(context)

    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Wake filter removed - bot responds during natural silence in conversation
    # Turn-taking is managed by LocalSmartTurnAnalyzerV3 and VAD

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi,  # RTVI processor
            stt,
            context_aggregator.user(),  # User responses
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            context_aggregator.assistant(),  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,  # Stop bot audio when user speaks
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )


    # # State tracking
    # participants = {}
    # active_speaker = None
    
    # async def update_context_state():
    #     """Update the LLM context with active speaker state."""
    #     # We only track active speaker in the persistent state message to avoid spamming the history.
    #     # Participants are now tracked via specific 'User joined/left' messages in the history.
    #     active_info = f"Active Speaker: {participants.get(active_speaker, 'Unknown')} (ID: {active_speaker})" if active_speaker else "Active Speaker: None"
        
    #     state_message = {
    #         "role": "system", 
    #         "content": f"Current Room Status:\n{active_info}"
    #     }
        
    #     # Search for existing state message to update in the context
    #     state_msg_index = -1
    #     for i, msg in enumerate(context.messages):
    #         if msg.get("content", "").startswith("Current Room Status:"):
    #             state_msg_index = i
    #             break
        
    #     if state_msg_index >= 0:
    #         context.messages[state_msg_index] = state_message
    #     else:
    #         context.messages.append(state_message)

    # @transport.event_handler("on_participant_joined")
    # async def on_participant_joined(transport, participant):
    #     nonlocal active_speaker
    #     # Safely get participant name with fallback
    #     participant_info = participant.get("info", {})
    #     participant_name = participant_info.get("userName") or participant_info.get("name") or "Guest"
    #     participant_id = participant["id"]
        
    #     participants[participant_id] = participant_name
    #     logger.info(f"Participant joined: {participant_name} (ID: {participant_id})")
        
    #     # Append event to history so the bot follows the flow
    #     context.messages.append({"role": "system", "content": f"{participant_name} has joined the conversation."})
        
    #     # Update active speaker state (incase it affects anything, though usually doesn't on join)
    #     await update_context_state()
        
    #     # Kick off the conversation with personalized greeting.
    #     # We add a specific instruction for the immediate response
    #     context.messages.append({"role": "system", "content": f"Greet {participant_name} by name."})
    #     await task.queue_frames([LLMRunFrame()])

    # @transport.event_handler("on_participant_left")
    # async def on_participant_left(transport, participant, reason):
    #     nonlocal active_speaker
    #     participant_id = participant["id"]
    #     if participant_id in participants:
    #         name = participants[participant_id]
    #         del participants[participant_id]
    #         logger.info(f"Participant left: {name} (ID: {participant_id})")
            
    #         # Append event to history
    #         context.messages.append({"role": "system", "content": f"{name} has left the conversation."})
            
    #         if active_speaker == participant_id:
    #             active_speaker = None
                
    #         await update_context_state()

    # @transport.event_handler("on_active_speaker_change")
    # async def on_active_speaker_change(transport, participant):
    #     nonlocal active_speaker
    #     # participant can be None if no one is speaking
    #     if participant:
    #          participant_id = participant["id"]
    #          if active_speaker != participant_id:
    #              active_speaker = participant_id
    #              if participant_id not in participants:
    #                   participant_info = participant.get("info", {})
    #                   participant_name = participant_info.get("userName") or participant_info.get("name") or "Guest"
    #                   participants[participant_id] = participant_name

    #              # ONLY update the state message, do not append to history to avoid spam
    #              await update_context_state()
    #              logger.debug(f"Active speaker changed to: {participants.get(participant_id, participant_id)}")
    #     else:
    #         if active_speaker is not None:
    #             active_speaker = None
    #             await update_context_state()
    #             logger.debug("Active speaker changed to: None")

    # @transport.event_handler("on_client_disconnected")
    # async def on_client_disconnected(transport, client):
    #     logger.info(f"Client disconnected")
    #     # await task.cancel()

    # Monitor shutdown event for OpenClaw
    async def monitor_shutdown():
        """Watch for shutdown_event and cancel task when triggered."""
        await shutdown_event.wait()
        logger.info("🛑 Shutdown signal received, stopping bot...")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    # Run bot with shutdown monitoring
    try:
        shutdown_monitor = asyncio.create_task(monitor_shutdown())
        await runner.run(task)
    except asyncio.CancelledError:
        logger.info("✅ Bot stopped gracefully")
    finally:
        # Clean up shutdown monitor
        if not shutdown_monitor.done():
            shutdown_monitor.cancel()


async def main(room_url: str, token: str, topic: str = None, personality_path: str = None):
    """Main entry point.
    
    Args:
        room_url: The Daily room URL to connect to.
        token: The Daily room token.
    """
    
    # Load agent identity from environment
    # MOLT_AGENT_NAME: Friendly name for wake phrases and display (e.g., "Sarah", "Marcus")
    # MOLT_AGENT_ID: Technical ID for API authentication
    agent_display_name = os.getenv("MOLT_AGENT_NAME") or os.getenv("MOLT_AGENT_ID", "Moltspaces Agent")
    logger.info(f"🤖 Bot will join as: {agent_display_name}")
    logger.info(f"� Connecting to room: {room_url}")

    # Create transport and join room
    logger.info(f"🚀 Joining Daily room...")
    transport = DailyTransport(
        room_url,
        token,
        agent_display_name,  # Use MOLT_AGENT_NAME as bot display name
        DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_user_tracks=False,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            # turn_analyzer=LocalSmartTurnAnalyzerV3(),
            enable_prejoin_ui=False,
        ),
    )
    
    runner_args = RunnerArguments()
    await run_bot(transport, runner_args, agent_display_name, topic, personality_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Moltspaces Voice Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run bot.py --url https://your-domain.daily.co/room --token <token>
        """
    )
    
    parser.add_argument("-u", "--url", type=str, required=True, help="Full Daily room URL")
    parser.add_argument("-t", "--token", type=str, required=True, help="Daily room token")
    
    parser.add_argument("--topic", type=str, help="Topic of the conversation")
    parser.add_argument("--personality", type=str, help="Path to personality file (markdown or text)")
    
    config = parser.parse_args()
    
    asyncio.run(main(room_url=config.url, token=config.token, topic=config.topic, personality_path=config.personality))

