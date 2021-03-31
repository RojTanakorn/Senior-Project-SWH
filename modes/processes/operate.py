import json
from .putaway import Putaway_mode
from .pickup import Pickup_mode
from .location_transfer import Location_transfer_mode


async def Operate(its_serial_number, payload_string):
    
    # Convert string to json (dict)
    payload_json = json.loads(payload_string)

    # Get current mode from payload
    current_mode = payload_json['mode']
    current_stage = payload_json['stage']
    
    # Call putaway mode function
    if current_mode == 2:
        await Putaway_mode(
            its_serial_number,
            payload_json,
            current_stage
        )

    # Call pickup mode function
    elif current_mode == 3:
        await Pickup_mode(
            its_serial_number,
            payload_json,
            current_stage
        )

    # Call location transfer mode function
    elif current_mode == 4:
        await Location_transfer_mode(
            its_serial_number,
            payload_json,
            current_stage
        )