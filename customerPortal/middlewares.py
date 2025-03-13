# from django.http import HttpResponseForbidden
# import ipaddress

# class BlockPrivateSubnetMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         client_ip = request.META.get('REMOTE_ADDR', '')

#         # Check if IP is in the 10.223.x.x subnet
#         if client_ip.startswith('10.223.'):
#             return HttpResponseForbidden("Access denied")

#         return self.get_response(request)