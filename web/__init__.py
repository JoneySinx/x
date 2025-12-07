from aiohttp import web
# ध्यान दें: हमने 'stream_routes' को 'route' से बदल दिया है क्योंकि पिछली फाइल route.py थी
from web.route import routes

def create_app():
    # client_max_size को 30MB तक बढ़ाना सुरक्षित है
    app = web.Application(client_max_size=30000000)
    app.add_routes(routes)
    return app

# यह ऑब्जेक्ट bot.py में इस्तेमाल होगा
web_app = create_app()
