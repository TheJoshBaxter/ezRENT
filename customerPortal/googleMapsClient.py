import googlemaps
import math
from django.conf import settings
from managementPortal.models import TransportRate

def calculate_delivery_fee(destination: str, rental_period, home_base: str = "1726 W 500 N, Springville, UT 84663") -> float:
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
        print("rental period:")
        print(rental_period)
        # Calculate the travel time from home_base to destination, then from the destination to the home base
        directions_to_dest = gmaps.directions(home_base, destination, mode="driving")
        directions_to_home = gmaps.directions(destination, home_base, mode="driving")
        
        # Extract travel time in seconds
        travel_time_to_dest = directions_to_dest[0]['legs'][0]['duration']['value']  # in seconds
        travel_time_to_home = directions_to_home[0]['legs'][0]['duration']['value']  # in seconds
        print("travel time to dest")
        print(travel_time_to_dest / 3600)
        print("travel time back to homebase")
        print(travel_time_to_home / 3600)

        base_thereNback_time = (travel_time_to_dest + travel_time_to_home) / 3600  # Convert seconds to hours
        
        # If rental period is >= 28 days, only charge one way travel fee
        if rental_period >= 28:
            # Total Service Time for a month-long rental is the base thereNback time plus 1/2 hour for load and unload equipment
            total_service_time_hours = base_thereNback_time + .5
            print("total service time for month-long rental (thereNback + .5):")
            print(total_service_time_hours)
        else:    
            # Total Service Time for a LESS THAN MONTH-LONG rental is the base thereNback time TIMES TWO plus 1 hour for load and unload equipment
            total_service_time_hours = (2 * base_thereNback_time) + 1
            print("total service time for LESS THAN MONTH-LONG rental (2x thereNback + 1)")
            print(total_service_time_hours)
        
        # Calculate the fee with a 2-hour minimum
        delivery_fee = max(total_service_time_hours, 2) * float(hourly_rate)  # max() ensures that the time used is at least 2 hours, hourly_rate defined in db (settings portal)
        print("total delivery fee")
        print(delivery_fee)

        return round(delivery_fee, 2)
    
    except Exception as e:
        print(f"Error calculating delivery fee: {e}")
        return 0.00

# # Example usage
# home_base_address = "1726 W 500 N, Springville, UT 84663"
# destination_address = "5232 W. Cannavale Ln., Herriman, UT 84096"
# rental_period = "blah blah"
# fee = calculate_delivery_fee(destination_address, rental_period, home_base=home_base_address)
# print(f"The delivery fee is bwahahaha: ${fee}")