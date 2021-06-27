from .putaway import Putaway_mode
from .pickup import Pickup_mode
from .location_transfer import Location_transfer_mode
from . import commons
from . import mode_selection_processes


''' Function for operating normal payload of mode process '''


async def Operate(hardware_id, payload_json):
    current_mode = payload_json['mode']
    current_stage = payload_json['stage']

    if current_mode == 2:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Putaway_mode(
            hardware_id, payload_json, current_stage
        )

    elif current_mode == 3:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Pickup_mode(
            hardware_id, payload_json, current_stage
        )

    elif current_mode == 4:
        log_dict, hardware_payload, webapp_payload, new_mode, new_stage = await Location_transfer_mode(
            hardware_id, payload_json, current_stage
        )

    await Processes_after_operate(
        log_dict, hardware_id, hardware_payload, webapp_payload, new_mode, new_stage
    )


async def Processes_after_operate(
    log_dict, hardware_id, hardware_payload, webapp_payload, new_mode, new_stage
):
    await commons.Store_log(log_dict)

    await commons.Notify_clients(hardware_id, hardware_payload, webapp_payload)

    if new_mode is not None:
        await commons.Update_current_mode_stage(hardware_id, new_mode, new_stage)


''' Function for Managing mode selection from webapp '''

async def Mode_selection_management(hardware_id, payload_json):
    new_mode = payload_json['new_mode']
    new_stage = payload_json['new_stage']
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

    await Processes_after_mode_selection(
        hardware_id, hardware_payload, webapp_payload, new_mode, new_stage
    )
    

async def Processes_after_mode_selection(
    hardware_id, hardware_payload, webapp_payload, new_mode, new_stage
):

    await commons.Notify_clients(hardware_id, hardware_payload, webapp_payload)
    await commons.Update_current_mode_stage(hardware_id, new_mode, new_stage)
