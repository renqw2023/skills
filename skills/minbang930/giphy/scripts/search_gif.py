#!/usr/bin/env python3
"""
Search Giphy for GIFs and return the most relevant result URL.
"""

import sys
import os
import json
import urllib.request
import urllib.parse

# Giphy API configuration
API_KEY = os.environ.get('GIPHY_API_KEY', 'YOUR_API_KEY_HERE')
API_ENDPOINT = "https://api.giphy.com/v1/gifs/search"

def search_gif(query, limit=1):
    """
    Search Giphy for GIFs matching the query.
    
    Args:
        query: Search term
        limit: Number of results to return (default: 1)
    
    Returns:
        dict: API response containing GIF results
    """
    if not API_KEY or API_KEY == 'YOUR_API_KEY_HERE':
        print("Error: GIPHY_API_KEY environment variable not set", file=sys.stderr)
        print("Get your API key from: https://developers.giphy.com/dashboard/", file=sys.stderr)
        return None
    
    # Build the API URL
    params = {
        'api_key': API_KEY,
        'q': query,
        'limit': limit,
        'rating': 'g',  # Safe for work
        'lang': 'en'
    }
    
    url = f"{API_ENDPOINT}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
            else:
                return None
    except Exception as e:
        print(f"Error searching Giphy: {e}", file=sys.stderr)
        return None

def get_top_gif_url(query):
    """
    Get the URL of the top GIF result for a query.
    
    Args:
        query: Search term
    
    Returns:
        str: URL to the GIF, or None if not found
    """
    results = search_gif(query, limit=1)
    
    if results and 'data' in results and len(results['data']) > 0:
        # Get the first result
        top_result = results['data'][0]
        # Return the URL - use 'url' field which is the Giphy page URL
        # Discord embeds Giphy URLs automatically
        if 'url' in top_result:
            return top_result['url']
    
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 search_gif.py <search_query>", file=sys.stderr)
        sys.exit(1)
    
    # Join all arguments as the search query
    query = ' '.join(sys.argv[1:])
    
    # Get the top GIF URL
    gif_url = get_top_gif_url(query)
    
    if gif_url:
        print(gif_url)
    else:
        print(f"No GIF found for query: {query}", file=sys.stderr)
        sys.exit(1)
