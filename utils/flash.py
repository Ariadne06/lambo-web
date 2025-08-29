# utils/flash.py
def set_flash(request, message, level="info"):
    request.session["__flash__"] = {"message": message, "message_level": level}

def get_flash(request):
    return request.session.pop("__flash__", {"message": None, "message_level": None})
