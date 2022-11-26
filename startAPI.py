import uvicorn

from lib.utils import CONFIG

if __name__=="__main__":
    try:
        uvicorn.run(
            "TknAcsWebAPI:app",
            host=CONFIG.get("WEB_API", "host"),
            port=CONFIG.get("WEB_API", "port"),
            reload=False,
            ssl_keyfile=CONFIG.get("WEB_API", "ssl_keyfile"),
            ssl_certfile=CONFIG.get("WEB_API", "ssl_certfile"),
        )
    except Exception as e:
        e.print()        
