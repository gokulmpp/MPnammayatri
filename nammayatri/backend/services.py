from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import RideRequest
from django.contrib.auth.decorators import login_required
import json
from channels.layers import get_channel_layer #type:ignore
from asgiref.sync import async_to_sync


@csrf_exempt
@login_required
def request_ride(request):
    if request.method == 'POST':
        user = request.user
        if user.role != 'customer':
            return JsonResponse({'error': 'Only customers can request rides'}, status=403)

        data = json.loads(request.body)
        from_location = data.get('from_location')
        to_location = data.get('to_location')

        if not from_location or not to_location:
            return JsonResponse({'error': 'Missing location details'}, status=400)

        # Calculate price (simple example)
        distance = calculate_distance(from_location, to_location)
        price = distance * 10  

        ride = RideRequest.objects.create(customer=user, from_location=from_location, to_location=to_location, price=price)

        # Notify all drivers via WebSockets
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "ride_requests",
            {
                "type": "new_ride",
                "message": f"New ride request from {user.email}!"
            }
        )

        return JsonResponse({'message': 'Ride requested successfully', 'ride_id': ride.id})
    
def calculate_distance(from_location, to_location):
    # Simple mock function for distance calculation
    return 5.0  # Example: fixed 5 km for now (can be replaced with Google Maps API)


@login_required
def available_rides(request):
    if request.user.role != 'driver':
        return JsonResponse({'error': 'Only drivers can see ride requests'}, status=403)

    rides = RideRequest.objects.filter(status='pending').values('id', 'customer__email', 'from_location', 'to_location', 'price')

    return JsonResponse({'available_rides': list(rides)})

@csrf_exempt
@login_required
def accept_ride(request, ride_id):
    if request.method == 'POST':
        user = request.user
        if user.role != 'driver':
            return JsonResponse({'error': 'Only drivers can accept rides'}, status=403)

        try:
            ride = RideRequest.objects.get(id=ride_id, status='pending')
            ride.status = 'accepted'
            ride.driver = user
            ride.save()
            return JsonResponse({'message': 'Ride accepted successfully'})
        except RideRequest.DoesNotExist:
            return JsonResponse({'error': 'Ride not found or already accepted'}, status=404)
