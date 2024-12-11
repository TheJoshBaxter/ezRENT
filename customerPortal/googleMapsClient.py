import googlemaps
import math
from django.conf import settings
from managementPortal.models import TransportRate

def calculate_delivery_fee(destination: str, home_base: str = "1726 W 500 N, Springville, UT 84663") -> float:
    """
    Calculate the delivery fee based on the travel time to the destination and back.
    
    Args:
        destination (str): The drop-off location address.
        home_base (str): The address of the home base. Default is "Your Home Base Address".
    
    Returns:
        float: The calculated delivery fee.
    """
    # Replace with your Google Maps API Key
    API_KEY = settings.G_MAPS_API
    gmaps = googlemaps.Client(key=API_KEY)

    # Grab rate from the DB
    hourly_rate = TransportRate.objects.first().hourly_rate
    print(hourly_rate)
    
    try:
        # Calculate the one-way travel time from home_base to destination
        directions_to_dest = gmaps.directions(home_base, destination, mode="driving")
        directions_to_home = gmaps.directions(destination, home_base, mode="driving")
        
        # Extract travel time in seconds
        travel_time_to_dest = directions_to_dest[0]['legs'][0]['duration']['value']  # in seconds
        travel_time_to_home = directions_to_home[0]['legs'][0]['duration']['value']  # in seconds
        print(home_base)
        
        # Total round trip travel time in hours
        total_travel_time_hours = (travel_time_to_dest + travel_time_to_home) / 3600  # Convert seconds to hours
        total_travel_time_hours = round(total_travel_time_hours, 2)
        total_travel_time_hours = float(total_travel_time_hours)
        print(total_travel_time_hours)

        # Add half hour for pickup and drop-off
        total_service_time_hours = float(total_travel_time_hours) + float(.5)  # Additional half hour
        
        # Calculate the fee with a 2-hour minimum
        delivery_fee = max(total_service_time_hours, 2) * hourly_rate  # max() ensures that the time used is at least 2 hours, hourly_rate defined in db (settings portal)
        print(delivery_fee)

        return round(delivery_fee, 2)
    
    except Exception as e:
        print(f"Error calculating delivery fee: {e}")
        return 0.00

# # Example usage
# home_base_address = "123 Main St, YourCity, YourState"
# destination_address = "456 Elm St, DestinationCity, DestinationState"
# fee = calculate_delivery_fee(destination_address, home_base=home_base_address)
# print(f"The delivery fee is: ${fee}")