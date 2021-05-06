import json
from .putaway import Putaway_mode
from .pickup import Pickup_mode
from .location_transfer import Location_transfer_mode
from . import commons
from . import mode_selection_processes


''' Function for operating normal payload of mode process '''
async def Operate(hardware_id, payload_string):
    
    # Convert string to json (dict)
    payload_json = json.loads(payload_string)

    # Get current mode from payload
    current_mode = payload_json['mode']
    current_stage = payload_json['stage']
    
    # Call putaway mode function
    if current_mode == 2:
        await Putaway_mode(
            hardware_id,
            payload_json,
            current_stage
        )

    # Call pickup mode function
    elif current_mode == 3:
        await Pickup_mode(
            hardware_id,
            payload_json,
            current_stage
        )

    # Call location transfer mode function
    elif current_mode == 4:
        await Location_transfer_mode(
            hardware_id,
            payload_json,
            current_stage
        )


''' Function for Managing mode selection from webapp '''
async def Mode_selection_management(hardware_id, payload_string):

    # Convert string to json (dict)
    payload_json = json.loads(payload_string)

    # Get new mode and stage from payload
    new_mode = payload_json['new_mode']
    new_stage = payload_json['new_stage']

    # Define hardware payload (as same as received payload from webapp)
    hardware_payload = commons.Payloads.mode_changed_to_hardware(new_mode, new_stage)

    # Call function according to new mode
    if new_mode == 0:
        webapp_payload = await mode_selection_processes.select_mode_0(hardware_id)

    elif new_mode == 2:
        webapp_payload = await mode_selection_processes.select_mode_2(hardware_id)

    elif new_mode == 3:
        webapp_payload = await mode_selection_processes.select_mode_3(hardware_id)

    elif new_mode == 4:
        webapp_payload = await mode_selection_processes.select_mode_4(hardware_id)

    # Update current mode and stage of specific hardware ID on HARDWARE_DATA
    await commons.Update_current_mode_stage(
        hardware_id=hardware_id,
        mode=new_mode,
        stage=new_stage
    )

    # Send payload to clients
    await commons.Notify_clients(
        hardware_id=hardware_id,
        hardware_payload=hardware_payload,
        webapp_payload=webapp_payload
    )
    