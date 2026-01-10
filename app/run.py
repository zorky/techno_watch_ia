import asyncio
import sys

if sys.platform == 'win32':
    # Force l'utilisation de ProactorEventLoop sur Windows
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web:app", host="0.0.0.0", port=8000, loop="asyncio")