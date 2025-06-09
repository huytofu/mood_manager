from TTS.api import TTS

# Load the XTTS model with better control parameters
MODEL_NAME = "tts_models/multilingual/multi-dataset/xtts_v2"
tts_model = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=True)

def get_tts_model():
    """Dependency to get the TTS model."""
    return tts_model 