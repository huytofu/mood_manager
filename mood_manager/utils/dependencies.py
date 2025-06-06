from TTS.api import TTS

# Load the pre-trained multi-speaker TTS model
MODEL_NAME = "tts_models/multilingual/multi-dataset/your_tts"
tts_model = TTS(model_name=MODEL_NAME, progress_bar=False, gpu=True)

def get_tts_model():
    """Dependency to get the TTS model."""
    return tts_model 