def get_available_heights(url: str) -> Set[int]:
    """Get available video heights from URL"""
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        # Убираем cookies чтобы избежать ошибок
    }
    
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get("formats") or []
            available_heights = set()
            
            for fmt in formats:
                if fmt.get("vcodec") in (None, "none"):
                    continue
                height = fmt.get("height")
                if isinstance(height, int):
                    available_heights.add(height)
            
            # Only expose common targets
            return {h for h in available_heights if h in {720, 1080, 1440, 2160}}
    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        # Fallback to basic formats
        return {720, 1080}

->

def get_available_heights(url: str) -> Set[int]:
    """Get available video heights from URL"""
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "format": "best[height<=2160]/best",
        "no_color": True,
        "ignoreerrors": True,
    }
    
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                logger.error("Failed to extract video info")
                return {720, 1080}
                
            formats = info.get("formats") or []
            available_heights = set()
            
            for fmt in formats:
                if fmt.get("vcodec") in (None, "none"):
                    continue
                height = fmt.get("height")
                if isinstance(height, int):
                    available_heights.add(height)
            
            # Only expose common targets
            result = {h for h in available_heights if h in {720, 1080, 1440, 2160}}
            if not result:
                logger.warning("No common heights found, using fallback")
                return {720, 1080}
            return result
    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        # Fallback to basic formats
        return {720, 1080}
