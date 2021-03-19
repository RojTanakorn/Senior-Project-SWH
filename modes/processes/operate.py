import json
from .putaway import Putaway_mode
from .pickup import Pickup_mode
from .location_transfer import Location_transfer_mode
from . import commons


''' Function for operating normal payload of mode process '''
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
            current_mode,
            current_stage
        )

    # Call pickup mode function
    elif current_mode == 3:
        await Pickup_mode(
            its_serial_number,
            payload_json,
            current_mode,
            current_stage
        )

    # Call location transfer mode function
    elif current_mode == 4:
        await Location_transfer_mode(
            its_serial_number,
            payload_json,
            current_mode,
            current_stage
        )


''' Function for Managing mode selection from webapp '''
async def Mode_selection_management(its_serial_number, payload_string):

    # Convert string to json (dict)
    payload_json = json.loads(payload_string)

    # Generate payload for sending to clients (hardware and webapp)
    hardware_payload, webapp_payload = commons.Payloads.mode_selection(
        payload_json['mode'],
        payload_json['stage']
    )

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=its_serial_number[2:],
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )
    