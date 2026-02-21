"""
Sarvam API service.
Handles audio transcription using Sarvam speech-to-text API.
"""

import requests
import tempfile
import os
from typing import List, Optional
import librosa
import numpy as np
from scipy.io import wavfile

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class SarvamError(Exception):
    """Custom exception for Sarvam API errors."""
    pass


# ===================================
# AUDIO CHUNKING
# ===================================

def split_audio_into_chunks(
    audio_url: str,
    chunk_duration: int = None
) -> List[str]:
    """
    Split audio into chunks for processing.
    
    Args:
        audio_url: Audio file URL
        chunk_duration: Chunk duration in seconds (default from settings)
        
    Returns:
        List of temporary chunk file paths
        
    Raises:
        SarvamError: If splitting fails
    """
    try:
        if chunk_duration is None:
            chunk_duration = settings.AUDIO_CHUNK_DURATION_SECONDS
        
        # Download audio
        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio.write(response.content)
            audio_path = temp_audio.name
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=None)
        
        # Clean up original temp file
        os.unlink(audio_path)
        
        # Get duration
        duration = librosa.get_duration(y=y, sr=sr)
        
        logger.info(
            "Audio loaded",
            duration_seconds=duration,
            sample_rate=sr
        )
        
        # If audio is shorter than chunk duration, return as-is
        if duration <= chunk_duration:
            chunk_path = _save_audio_chunk(y, sr, 0)
            return [chunk_path]
        
        # Split into chunks
        total_samples = len(y)
        samples_per_chunk = sr * chunk_duration
        chunks = []
        
        for start_sample in range(0, total_samples, samples_per_chunk):
            end_sample = min(start_sample + samples_per_chunk, total_samples)
            chunk = y[start_sample:end_sample]
            
            chunk_path = _save_audio_chunk(chunk, sr, start_sample // samples_per_chunk)
            chunks.append(chunk_path)
        
        logger.info(
            "Audio split into chunks",
            chunk_count=len(chunks),
            chunk_duration=chunk_duration
        )
        
        return chunks
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error("Audio URL not found", url=audio_url)
            raise SarvamError("Audio file could not be found or is inaccessible (404)")
        logger.error("HTTP error during audio download", error=str(e))
        raise SarvamError(f"HTTP error during audio download: {str(e)}")
    except Exception as e:
        logger.error("Failed to split audio", error=str(e))
        raise SarvamError(f"Failed to split audio: {str(e)}")


def _save_audio_chunk(audio_data: np.ndarray, sample_rate: int, chunk_index: int) -> str:
    """
    Save audio chunk to temporary WAV file.
    
    Args:
        audio_data: Audio data array
        sample_rate: Sample rate
        chunk_index: Chunk index
        
    Returns:
        Path to temporary file
    """
    # Normalize to 16-bit PCM
    audio_pcm = np.int16(audio_data / np.max(np.abs(audio_data)) * 32767)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(suffix=f'_chunk_{chunk_index}.wav', delete=False) as temp_file:
        wavfile.write(temp_file.name, sample_rate, audio_pcm)
        return temp_file.name


# ===================================
# TRANSCRIPTION
# ===================================

def transcribe_audio_chunk(
    audio_file_path: str,
    language_code: str = None
) -> str:
    """
    Transcribe a single audio chunk using Sarvam API.
    
    Args:
        audio_file_path: Path to audio file
        language_code: Language code (default: auto-detect)
        
    Returns:
        Transcribed text
        
    Raises:
        SarvamError: If transcription fails
    """
    try:
        if language_code is None:
            language_code = settings.SARVAM_LANGUAGE_CODE
        
        # Prepare request
        headers = {
            'api-subscription-key': settings.SARVAM_API_KEY
        }
        
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'file': ('audio.wav', audio_file, 'audio/wav')
            }
            
            data = {
                'model': settings.SARVAM_MODEL,
                'language_code': language_code
            }
            
            # Call Sarvam API
            response = requests.post(
                settings.SARVAM_API_ENDPOINT,
                headers=headers,
                files=files,
                data=data,
                timeout=120
            )
        
        # Clean up temporary file
        try:
            os.unlink(audio_file_path)
        except:
            pass
        
        # Check response
        if response.status_code != 200:
            logger.error(
                "Sarvam API error",
                status_code=response.status_code,
                response=response.text
            )
            raise SarvamError(f"Sarvam API error: {response.status_code}")
        
        # Extract transcript
        result = response.json()
        transcript = result.get('transcript', '')
        
        if not transcript:
            logger.warning("Empty transcript received from Sarvam API")
        
        return transcript
        
    except requests.exceptions.Timeout:
        logger.error("Sarvam API timeout")
        raise SarvamError("Transcription timeout")
    except requests.exceptions.RequestException as e:
        logger.error("Sarvam API request failed", error=str(e))
        raise SarvamError(f"Transcription request failed: {str(e)}")
    except Exception as e:
        logger.error("Transcription failed", error=str(e))
        raise SarvamError(f"Transcription failed: {str(e)}")


def transcribe_audio(
    audio_url: str,
    language_code: str = None
) -> str:
    """
    Transcribe complete audio file (with chunking if needed).
    
    Args:
        audio_url: Audio file URL
        language_code: Language code (default: auto-detect)
        
    Returns:
        Complete transcript
        
    Raises:
        SarvamError: If transcription fails
    """
    try:
        # Split audio into chunks
        chunks = split_audio_into_chunks(audio_url)
        
        logger.info(
            "Starting transcription",
            chunk_count=len(chunks)
        )
        
        # Transcribe each chunk
        transcripts = []
        for i, chunk_path in enumerate(chunks):
            try:
                chunk_transcript = transcribe_audio_chunk(chunk_path, language_code)
                transcripts.append(chunk_transcript)
                
                logger.info(
                    "Chunk transcribed",
                    chunk_index=i+1,
                    total_chunks=len(chunks)
                )
                
            except Exception as e:
                logger.error(
                    "Chunk transcription failed",
                    chunk_index=i+1,
                    error=str(e)
                )
                # Continue with other chunks
                transcripts.append("")
        
        # Concatenate transcripts
        full_transcript = " ".join(transcripts).strip()
        
        if not full_transcript:
            logger.warning("No speech detected in audio - possibly music or silence")
            raise SarvamError("No speech detected in audio. It appears to be music or silence.")

        logger.info(
            "Transcription completed",
            transcript_length=len(full_transcript),
            word_count=len(full_transcript.split())
        )
        
        return full_transcript
        
    except Exception as e:
        logger.error("Audio transcription failed", error=str(e))
        raise SarvamError(f"Audio transcription failed: {str(e)}")


# ===================================
# HELPER FUNCTIONS
# ===================================

def validate_audio_url(audio_url: str) -> bool:
    """
    Validate that audio URL is accessible.
    
    Args:
        audio_url: Audio URL
        
    Returns:
        True if valid and accessible
    """
    try:
        response = requests.head(audio_url, timeout=10)
        return response.status_code == 200
    except:
        return False


def get_audio_duration(audio_url: str) -> Optional[float]:
    """
    Get audio duration in seconds.
    
    Args:
        audio_url: Audio URL
        
    Returns:
        Duration in seconds or None if failed
    """
    try:
        response = requests.get(audio_url, timeout=60)
        response.raise_for_status()
        
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
            temp_audio.write(response.content)
            audio_path = temp_audio.name
        
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        
        os.unlink(audio_path)
        
        return duration
        
    except Exception as e:
        logger.error("Failed to get audio duration", error=str(e))
        return None