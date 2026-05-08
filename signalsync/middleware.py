class AppendSlashMiddleware:
    """
    Silently adds a trailing slash before URL resolution if one is missing.

    Unlike Django's APPEND_SLASH=True, this does NOT issue a 301 redirect,
    so POST requests work correctly without losing the request body.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path_info.endswith("/"):
            request.path_info = request.path_info + "/"
            request.META["PATH_INFO"] = request.path_info
        return self.get_response(request)
