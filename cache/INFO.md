# Speaker Embedding Cache System

This system provides caching for speaker embeddings with a simplified in-memory approach.

## 🎯 Features

- **In-Memory Caching**: Fast, simple caching during application runtime
- **Graceful Degradation**: Works without external dependencies
- **Simple API**: Clean endpoints for cache operations
- **Auto-Cleanup**: Cache cleared on application restart

## 🔧 Configuration

The cache system now uses a simplified in-memory approach that requires no external configuration. Speaker embeddings are cached in memory during the application session.

## 📡 API Endpoints

### Core Operations
- `POST /cache_user_voice` - Cache speaker embedding
- `GET /cache_status/{user_id}` - Check cache status
- `DELETE /clear_user_cache/{user_id}` - Clear user cache

### Management
- `POST /cleanup_cache` - Manual cache cleanup

## 🚀 Usage Flow

1. **Initial Setup**: User uploads voice sample
```bash
POST /cache_user_voice
{
  "user_id": "user123"
}
```

2. **Generate Meditations**: All generation endpoints use cached embedding
```bash
POST /generate_release_meditation_audio
{
  "user_id": "user123",
  "selected_emotion": "stress",
  "selected_tone": "calm",
  "min_length": 10,
  "background_options": {...}
}
```

3. **Check Status**: Verify cache status
```bash
GET /cache_status/user123
```

## 📊 Performance Benefits

### Before (No Cache)
- Speaker embedding generation: ~2-5 seconds per request
- CPU/GPU intensive operation every time

### After (With Cache)
- First request: ~2-5 seconds (generation + caching)
- Subsequent requests: ~50-200ms (cache retrieval)
- 10-100x performance improvement

## 🛠 Architecture

```
Cache Manager
└── In-Memory Cache (Dictionary-based)
```

### File Structure
- `cache_manager.py` - Unified cache interface with in-memory storage
- `app.py` - FastAPI endpoints using cache

## 🔍 Monitoring

### Cache Status Response
```json
{
  "user_id": "user123",
  "cached": true,
  "message": "Speaker embedding found",
  "configured_backend": "redis",
  "active_backend": "in-memory",
  "status": "fallback_only",
  "fallback_entries": 5
}
```

## 🔒 Data Management

### Lifecycle
- **Storage**: Embeddings stored in application memory
- **Persistence**: Cache cleared on application restart
- **Security**: No disk storage, memory-only approach

## 📈 Scaling Considerations

### Current Limitations
- Cache lost on application restart
- Memory usage grows with number of users
- Single-instance only (no sharing between app instances)

### Future Enhancements
For production deployments with persistence requirements, consider:
- Redis for high-performance persistent caching
- MongoDB for integrated database storage
- File-based caching for simple persistence

## 🐛 Troubleshooting

### Cache Issues
1. **Cache Missing**: Normal after application restart
2. **Memory Usage**: Monitor with `/cache_status` endpoint
3. **Performance**: Cache hit rates visible in status endpoint

## 🚦 Quick Start

1. **Start Application**
```bash
python app.py
```

2. **Test Cache**
```bash
curl -X POST http://localhost:8000/cache_user_voice?user_id=test123
curl http://localhost:8000/cache_status/test123
```

## 💡 Notes

This simplified caching approach prioritizes:
- **Simplicity**: No external dependencies
- **Development Speed**: Quick setup and testing
- **Reliability**: No database connection failures

For production use with persistence requirements, the system can be easily extended to include Redis or MongoDB backends. 