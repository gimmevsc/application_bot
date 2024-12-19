from shared.config import DEVELOPMENT


if __name__ == "__main__":
    if DEVELOPMENT:
        import asyncio
        from bot import polling

        asyncio.run(polling())

    else:
        import uvicorn
        from app import app

        uvicorn.run(app, host="0.0.0.0", port=5000)
