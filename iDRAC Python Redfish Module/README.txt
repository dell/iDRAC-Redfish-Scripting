# IdracRedfishSupport Module

## Module Overview

Python module for iDRAC Redfish support to allow the user to perform multiple workflows. This module can be imported from python prompt to start an interactive session with the iDRAC to perform multiple operations. Some workflow examples include configuration changes, firmware updates, exporting logs and SupportAssist collection. See module function section below for all supported workflows.

## Prerequisites

- Python 3.x version installed (latest version recommended)
- Requests module installed. (pip3 install requests)

## Install Module

- pip3 install IdracRedfishSupport

Note: Besides IdracRedfishSupport module getting installed pip3 will also install all standalone python scripts from the Python directory on GitHub. 

## Supported Module Functions

    assign_disk_hotspare(script_examples='', hotspare_type='', disk_fqdd='', virtual_disk_fqdd='default')
        Function to assign disk hotspare, global or dedicated. Supported function arguments: hotspare_type (supported values are dedicated or global), disk_fqdd and virtual_disk_fqdd (only required if assigning dedicated hotspare).

    bios_device_recovery(script_examples='')
        Function to recover corrupted server BIOS. During this process, server will power OFF, power ON, recover the BIOS firmware, reboot and process will be complete. Check iDRAC Lifecycle Logs for more details/status on the recovery process.

    boot_to_network_iso(script_examples='', attach_iso='', detach_iso='', get_attach_status='', share_ip='', share_type='', share_name='', image_name='', share_username='')
        Function to either get network ISO attach status, boot to network ISO or detach network ISO. When you execute function to attach ISO and attach is successful, server will automatically reboot. Supported function arguments: attach_iso (supported value: True), detach_iso (supported value: True), get_attach_status (supported value: True), share_ip, share_name, image_name, share_username (only required for CIFS share) and share_type (supported values: NFS and CIFS. Note: If using CIFS share it will prompt you to enter CIFS share password).

    change_bios_boot_order(script_examples='', boot_order_devices='', reboot='')
        Function to change BIOS boot order. Supported function arguments: boot_order_devices (possible value: pass in one or multiple boot order device IDs. If passing in multiple devices, use a comma separator. NOTE: If needed, execute IdracRedfishSupport.get_current_bios_boot_order() to get boot order devices). reboot (possible values: yes and no. If you pass in no for reboot, the config job is still created and will execute on next server manual reboot).

    change_bios_password(script_examples='', password_type='', set_password='', change_password='', delete_password='', reboot='')
        Function to set, change or delete BIOS passwords. Script will prompt you to enter password strings. Supported function arguments: password_type (supported values: SysPassword, SetupPassword, PersistentMemPassphrase), set_password (supported_value: True), change_password (supported_value: True), delete_password (supported_value: True) and reboot (supported values: yes and no).

    check_consistency_virtual_disk(script_examples='', virtual_disk_fqdd='')
        Function to check consitency for a virtual disk. Supported function argument: virtual_disk_fqdd.

    clear_foreign_config_controller(script_examples='', controller_fqdd='')
        Function to clear foreign configuration for storage controller. Supported function argument: controller_fqdd.
		
    convert_drives_RAID(script_examples='', drives='')
        Function to convert drives from non RAID(non ready) to RAID(ready) state. Supported function argument: drives (possible values: pass in one more multiple disk FQDDs. If passing in multiple disk FQDDs, use comma separator).

    convert_drives_nonRAID(script_examples='', drives='')
        Function to convert drives from RAID(ready) to non RAID(not ready) state. Support function argument: drives (possible values: pass in one more multiple disk FQDDs. If passing in multiple disk FQDDs, use comma separator).

    create_delete_iDRAC_subscriptions(script_examples='', get_subscriptions='', create_subscription='', destination_uri='', event_format_type='', event_type='', submit_test_event='', delete_subscription_uri='', message_id='')
        Function to either get current iDRAC subscriptions, create new subscription, submit test event to a location or delete subscription. Supported function arguments: get_subscriptions(supported value: True), create_subscription(supported value: True), destination_uri (pass in complete HTTPS URI path), event_format_type(supported values: Event, MetricReport or None), event_type(supported values: StatusChange, ResourceUpdated, ResourceAdded, ResourceRemoved, Alert, MetricReport), submit_test_event(possible value: True), message_id (pass in the message ID to submit test event, example: PDR1101) and delete_subscription_uri (pass in complete subscription URI. If needed execute IdracRedfishSupport.create_delete_iDRAC_subscriptions(get_subscriptions=True) to get subscription URIs).

    create_modify_delete_iDRAC_users(script_examples='', get_current_users='', create_user='', new_username='', user_id='', role_id='', enable_user='', disable_user='', modify_user='', delete_user='', change_password='')
        Function to create, modify or delete iDRAC user accounts. Supported function arguments: script_examples (supported value: True), get_current_users (supported value: True), create_user (supported value: True), new_username, user_id (possible values: 2 thru 16), role_id (supported values: Administrator, Operator, ReadOnly and None), enable_user (supported value: True), disable_user (supported_value: True), modify_user (supported value: pass in user ID you want to modify, 2 thru 16), delete_user (supported value: pass in the user ID you want to delete, 2 thru 16) and change_password.

    change_virtual_disk_attributes(script_examples="", vd_fqdd="", diskcachepolicy="", readcachepolicy="", writecachepolicy=""):
       Function to change virtual disk attributes. Supported function arguments: vd_fqdd (possible value: VD FQDD), diskcachepolicy (possible values: Enabled and Disabled), readcachepolicy (Off, ReadAhead and AdaptiveReadAhead), writecachepolicy (ProtectedWriteBack, UnprotectedWriteBack and WriteThrough).

    create_virtual_disk(script_examples="", controller_fqdd="", disk_fqdds="", raid_level="", vd_name="", vd_size="", vd_stripesize="", secure="", diskcachepolicy="", readcachepolicy="", writecachepolicy=""):
       Function to create virtual disk. Function arguments: controller_fqdd, disk_fqdds (if you\'re passing in multiple drives for VD creation, pass them in as a list), raid_level, supported integer values: 0, 1, 5, 6, 10, 50 and 60 (not all RAID levels are supported on each storage contoller), vd_name is optional (if not passed in, controller will set using default name), vd_size is optional (integer value in bytes) and if not passed in VD creation will use the full disk size, vd_stripesize is optional (integer value in bytes) and if not passed in controller will assign the default stripesize for the RAID level, secure is optional (pass in value of True to secure the VD during VD creation), diskcachepolicy is optional (possible values: Enabled and Disabled), readcachepolicy is optional (Off, ReadAhead and AdaptiveReadAhead), writecachepolicy (ProtectedWriteBack, UnprotectedWriteBack and WriteThrough).

    delete_iDRAC_job_id_or_job_queue(script_examples='', job_id='')
        Function to either delete single job ID or clear the job queue. Supported function argument: job_id (pass in either job ID to delete single job or string "clear" to delete all jobs in the job queue. If needed, execute IdracRedfishSupport.get_iDRAC_current_job_queue() to get current iDRAC job queue.

    delete_iDRAC_session(script_examples='', session_id='')
        Function to delete one current iDRAC session. Supported function argument: session_id (pass in integer value of the session ID to delete. If needed, execute get_current_iDRAC_sessions() to get session IDs.)

    delete_virtual_disk(script_examples='', virtual_disk_fqdd='')
        Function to delete storage controller virtual disk. Supported function argument: virtual_disk_fqdd (pass in virtual disk FQDD string)

    export_clear_serial_datalogs(script_examples='', enable_capture_serial='', export_serial_data='', clear_serial_data='', disable_capture_serial='')
        Function to either enable serial data capture, export serial data or clear serial data. NOTE: This feature requires iDRAC Datacenter license. Supported function arguments: enable_capture_serial (possible value: True), export_serial_data (possible value: True), clear_serial_data (possible value: True), disable_capture_serial (possible value: True).

    export_hardware_inventory(script_examples='', get_supported_share_types='', export_hw_inventory='', share_ip='', share_type='', share_name='', share_username='', share_password='', ignore_cert_warning='', filename='')
        Function to export server hardware inventory locally or network shares. Supported function arguments: get_supported_share_types (possible value: True, export_hw_inventory (possible value: True), share_type (execute IdracRedfishSupport.export_hardware_inventory(get_supported_share_types=True) to get supported share type values), share_ip, share_name, share_username (required for CIFS or auth enabled for HTTP/HTTPS), share_userpassword (required for CIFS or auth enabled for HTTP/HTTPS), ignore_cert_warning (possible values: Off and On). This argument is only supported for HTTPS share) and filename (pass in an unique string name with .xml extension (HW inventory will only be exported in XML format).

    export_iDRAC_lifecycle_logs(script_examples='', get_supported_share_types='', export_lc_logs='', share_ip='', share_type='', share_name='', share_username='', share_password='', ignore_cert_warning='', filename='')
        Function to export iDRAC Lifecycle (LC) logs locally or network shares. Supported function arguments: get_supported_share_types (possible value: True, export_lc_logs (possible value: True), share_type (execute IdracRedfishSupport.export_iDRAC_lifecycle_logs(get_supported_share_types=True), share_ip, share_name, share_username (if auth is enabled), share_userpassword (if auth is enabled), ignore_cert_warning (possible values: Off and On). This argument is only supported for HTTPS share) and filename (pass in an unique string name with .xml extension (iDRAC LC logs will only be exported in XML format). Execute examples: IdracRedfishSupport.export_iDRAC_lifecycle_logs(share_type="local",filename="R640_lc_logs.xml") and IdracRedfishSupport.export_iDRAC_lifecycle_logs(share_type="NFS",share_ip="192.168.0.130",share_name="/nfs",filename="R640_LC_logs.xml").

    export_import_iDRAC_certs(script_examples='', get_current_certs='', export_cert='', import_cert='', cert_filename='', cert_passphrase='')
        Function to either get current iDRAC certificates or export/import certificates. Supported function arguments: export_cert (possible values: Server, CSC, CA or ClientTrustCertificate), import_cert (possible values: Server, CSC, CA or ClientTrustCertificate), cert_filename (pass in the name of the cert file to import which must be in base64 string format) and cert_passphrase (pass in passphrase if cert is protected for import).

    export_import_iDRAC_license(script_examples='', get_license_info='', get_network_share_types='', license_id='', export_license='', import_license='', delete_license='', share_ip='', share_type='', share_name='', share_username='', share_password='', license_filename='', ignore_certwarning='')
        Function to manage iDRAC licenses, either get license info, export/import license using local/network share or delete license. Supported function arguments: get_license_info (supported value: True), get_network_share_types (supported value: True), export_license (supported value: True). Note: Export locally, license will be in base64 string format. Export to network share, license will be in XML format., import_license (supported value: True). Note: If you import license locally, the license file must be either in base64 string format or XML extension. If you import from network share license must be in XML format, delete_license (supportd value: True), license_id (pass in license ID string which is needed for export and delete), share_ip, share_type, share_name, share_username (only required for CIFS and HTTP/HTTPS using auth), share_password (only required for CIFS and HTTP/HTTPS using auth), ignore_certwarning (only optional for HTTPS) and license_filename (required for import local, export to network share pass in an unique string name for the license file).

    export_import_server_configuration_profile_local(script_examples='', export_profile='', export_format='', targets='', export_use='', include_in_export='', import_profile='', import_filename='', shutdown_type='', end_host_powerstate='')
        Function to export or import server configuration profile (SCP) locally. Supported function arguments: export_profile (supported value: True), export_format (supported values: XML or JSON), targets (supported values: ALL, IDRAC, BIOS, NIC, FC, RAID, System, LifecycleController, EventFilters) Note, you can pass in one or multiple values. If passing in multiple values, use comma separator with no whitespace. export_use (supported value: Clone) Note: Argument is optional, if not used iDRAC will export as default. include_in_export (supported_values: IncludeReadOnly or IncludePasswordHashValues) Note: If you pass in multiple values, use comma separator with no whitespace. Argument is optional, if not used iDRAC will export as default. import_profile (supported value: True), import_filename (pass in SCP filename), shutdown_type (supported values: Forced, Graceful and NoReboot). Note: optional, if not passed in server will perform graceful. end_host_powerstate (possible values: On and Off). Note: optional, if not used default value is On.

    export_import_server_configuration_profile_network_share(script_examples='', export_profile='', export_format='', targets='', export_use='', include_in_export='', share_type='', share_ip='', share_name='', share_username='', share_password='', ignore_certwarning='', import_profile='', filename='', shutdown_type='', end_host_powerstate='')
        Function to export or import server configuration profile (SCP) using a network share. Supported function arguments: export_profile (supported value: True), export_format (supported values: XML or JSON), targets (supported values: ALL, IDRAC, BIOS, NIC, FC, RAID, System, LifecycleController, EventFilters) Note, you can pass in one or multiple values. If passing in multiple values, use comma separator with no whitespace. export_use (supported value: Clone) Note: Argument is optional, if not used iDRAC will export as default. include_in_export (supported_values: IncludeReadOnly or IncludePasswordHashValues) Note: If you pass in multiple values, use comma separator with no whitespace. Argument is optional, if not used iDRAC will export as default. share_type (supported values: NFS, CIFS, HTTP and HTTPS), share_ip, share_name, share_username, share_password, ignore_certwarning (only valid for HTTPS and is optional, supported values On and Off), import_profile (supported value: True), filename (pass in unique SCP filename), shutdown_type (supported values: Forced, Graceful and NoReboot). Note: optional, if not passed in server will perform graceful. end_host_powerstate (possible values: On and Off). Note: optional, if not used default value is On.

    export_server_factory_configuration(script_examples='', get_supported_share_types='', export_factory_config='', share_ip='', share_type='', share_name='', share_username='', share_password='', ignore_cert_warning='', filename='')
        Function to export server factory configuration to a network share. Supported function arguments: get_supported_share_types (possible value: True, export_factory_config (possible value: True), share_type, share_ip, share_name, share_username (required for CIFS and HTTP/HTTPS if auth is enabled), share_userpassword (required for CIFS and HTTP/HTTPS if auth is enabled), ignore_cert_warning (possible values: Off and On). This argument is only supported for HTTPS share) and filename (pass in an unique string name with .xml extension (factory inventory will only be exported in XML format).

    export_server_screen_shot(script_examples='', file_type='')
        Function to export server screenshot saved by iDRAC. This image will be exported in base64 format to a file. You will need to take this content and use a utility which can convert base64 to PNG for viewing the image. Supported function argument: file_type (supported values: LastCrashScreenShot, Preview and ServerScreenShot. NOTE: Make sure to pass in the exact case value).

    export_server_thermal_history(script_examples='', get_supported_share_types='', export_thermal_history='', share_ip='', share_type='', share_name='', share_username='', share_password='', filename='', file_type='')
        Function to export server thermal history to a network share. Supported function arguments: get_supported_share_types (possible value: True), export_thermal_history (possible value: True), share_type, share_ip, share_name, share_username (required for CIFS only), share_userpassword (required for CIFS only), filename (pass in unique failename), file_type (pass in file type for exported file, either CSV or XML.

    export_server_video_log(script_examples='', file_type='')
        Function to export server video log saved by iDRAC. Supported function argument: file_type(supported values: BootCaptureVideo and CrashCaptureVideo. NOTE: make sure to pass in the exact case value). Extract the video files(dvc format) from the zip to view them.

    export_support_assist_collection(script_examples='', get_supported_share_types='', export_collection='', share_ip='', share_type='', share_name='', share_username='', share_password='', filter_pii='', data_selector='')
        Function to export SupportAssist collection either locally or to a network share. Supported function arguments: get_supported_share_types (supported value: True), export_collection (supported value: True), share_ip, share_type, share_name, share_username, share_password, filter_pii (supported values: No and Yes) and data_selector (supported values: DebugLogs, HWData, OSAppData, TTYLogs and TelemetryReports. You can pass in one or multiple values. If passing in multiple, use a comma separator. Supported values are also case sensitive).

    firmware_update_multipart_upload(script_examples='', get_fw_inventory='', fw_image_path='', reboot='')
        Function to either get current firmware inventory or update firmware for one supported device. Supported function arguments: (get_fw_inventory (possible value: True), firmware_image_path (pass in the complete directory path with firmware image name. Firmware image must be Windows Dell Update Package EXE file) and reboot (supported values: yes and no). Reboot server is required for certain devices to apply the firmware (Examples: BIOS, NIC, PERC). Refer to iDRAC user guide update section for more details.

    generate_replace_iDRAC_CSR(script_examples='', get_current_certs='', generate_CSR='', city='', state='', country='', common_name='', org='', orgunit='', email='', replace_CSR='', CSR_filename='')
        Function to either get current iDRAC certs or generate new CSR. Supported function arguments: get_current_certs (possible value: True), generate_CSR (possible value: True), city, state, country, common_name, org, orgunit, email (optional), replace_CSR (pass in the cert ID of the cert you want to replace. If needed, execute IdracRedfishSupport.generate_iDRAC_CSR(get_current_certs=True) to get the cert ID. Example: SecurityCertificate.1), CSR_filename (pass in name of signed CSR filename).

    get_bios_attribute_registry(script_examples='', attribute_name='')
        Function to get BIOS attribute registry. Getting attribute information is helpful to configure BIOS attributes (get supported possible values, dependencies, attribute type). Default behavior will get the complete BIOS attribute registry. Supported function argument: attribute_name (pass in exact BIOS string name value due to case sensitive.

    get_bios_attributes(script_examples='', attribute_name='')
        Function to get BIOS attributes with their current settings. Use attribute_name function argument to only return details for a specific attribute. NOTE: Make sure to pass in exact attribute name string due to case sensitive support.

    get_current_bios_boot_order(script_examples='')
        Function to get current BIOS boot mode and boot order.

    get_current_iDRAC_sessions(script_examples='')
        Function to get current active iDRAC sessions.

    get_current_server_power_state(script_examples='')
        Function to get current server power state and supported possible values for changing server power state

    get_iDRAC_attribute_registry(script_examples='', attribute_name='')
        Function to get iDRAC attribute registry. Getting attribute information is helpful to configure iDRAC attributes (get supported possible values, dependencies, attribute type). Supported function argument: attribute_name.

    get_iDRAC_attributes(script_examples='', group_name='', attribute_name='')
        Function to get iDRAC attributes which also includes Lifecycle Controller and System attributes. Supported function arguments: group_name (supported values: idrac, lc and system) and attribute_name (pass in attribute name if you only want to return details for a specific attribute.

    get_iDRAC_current_job_queue(script_examples='')
        Function to get current iDRAC job queue.

    get_message_registry(script_examples='', message_id='')

    get_pcie_device_or_function_inventory(script_examples='', user_input='')
        Function to get either PCIe device or PCIe function inventory data. Supported function argument: user_input (supported values: "device" or "function").

    get_remote_service_api_status(script_examples='')
        Function to get the server remote services status. This will return: lifecycle controller(LC) status, real time monitoring (RT) status, overall server status, Telemetry status(if supported) and overall status.

    get_server_slot_information(script_examples='')
        Function to get server slot information. This includes PSUs, Fans, DIMMs, CPUs, IDSDM, vFlash, PCIe, and disks.

    get_set_chassis_indicator_LED(script_examples='', get_LED_status='', set_LED='')
        Function to either get current chassis LED status or blink chassis LED. Supported function arguments: script_examples (supported value: True), get_LED_status (supported value: True) and set_LED (supported values: Blinking and Lit).

    get_storage_controller_details(script_examples='', controller_fqdd='')
        Function to get details for a specific storage controller. Supported function argument: controller_fqdd

    get_storage_controllers(script_examples='')
        Function to get server storage controller FQDDs

    get_storage_disk_details(script_examples='', controller_fqdd='')
        Function to get detailed information for all drives detected behind storage controller. Supported function argument: controller_fqdd

    get_storage_disks(script_examples='', controller_fqdd='')
        Function to get drive FQDDs for storage controller. Supported function argument: controller_fqdd

    get_storage_enclosures(script_examples='')
        Function to get server storage enclosure(s)

    get_virtual_disk_details(script_examples='', controller_fqdd='')
        Function to get details for all virtual disks behind storage controller. Supported function argument: controller_fqdd

    get_virtual_disks(script_examples='', controller_fqdd='')
        Function to get virtual disk FQDDs for storage controller. Supported function argument: controller_fqdd

    import_foreign_config_controller(script_examples='', controller_fqdd='')
        Function to import foreign configuration for storage controller. Supported function argument: controller_fqdd.

    initialize_virtual_disk(script_examples='', virtual_disk_fqdd='', init_type='')
        Function to initialize virtual disk. Supported function arguments: virtual_disk_fqdd and init_type (supported values: Fast and Slow).

    install_from_repository(script_examples='', get_fw_inventory='', get_repo_update_list='', get_device_name_criticality_info='', repository_update='', share_ip='', share_type='', share_name='', share_username='', share_password='', apply_update='', reboot_needed='', catalog_file='', ignore_certwarning='')
        Function to either get current firmware inventory, get repository update list details, criticality repository details or perform install from repository. Supported arguments and possible values: get_fw_inventory (supported value: True), get_repo_update_list (supported value: True), get_device_name_criticality_info (supported_value: True), repository_update (supported value: True), share_ip, share_type (supported values: NFS, CIFS, HTTP and HTTPS), share_name, share_username (only required if using CIFS or secure HTTP/HTTPS), share_password (only required if using CIFS or secured HTTP/HTTPS), apply_update (supported values: yes and no), reboot_needed (supported values: yes and no), catalog_file (only required if default catalog name is not used (Catalog.xml)), ignore_certwarning (supported values: On and Off, only valid to use with HTTPS. If not passed in, default value is On)

    manage_iDRAC_time(script_examples='', get_time='', set_time='')
        Function to either get or set iDRAC time. Supported function arguments: get_time (supported value: True) and set_time (NOTE: execute get_time argument to see the correct date/time format to use).

    preview_server_configuration_profile_local(script_examples='', profile_name='')
        Function to preview server configuration profile locally. Supported function parameters: script_examples (supported value: True) and profile_name (pass in the string name of your profile).

    preview_server_configuration_profile_network_share(script_examples='', profile_name='', share_ip='', share_name='', share_type='', share_username='', share_password='', ignore_certwarning='')
        Function to preview server configuration profile (SCP) from a network share. Supported function arguments: profile_name (pass in name of profile), share_type (supported values: NFS, CIFS, HTTP and HTTPS), share_ip, share_name, share_username, share_password, ignore_certwarning (only valid for HTTPS and is optional, supported values On and Off)

    rekey_storage_controller_key(script_examples='', controller_fqdd='', encryption_mode='', key_id='default')
        Function to rekey storage controller key (Local Key Management (LKM) or Secure Enterprise Key Manager (SEKM). Supported function arguments: controller_fqdd, encryption_mode (supported values are SEKM or LKM) and key_id (only supported for LKM, you can pass in either current string value set or change to a new string value). If LKM rekey is being performed, function will prompt you to enter current key passphrase, then set new key passphrase.

    remove_storage_controller_key(script_examples='', controller_fqdd='')
        Function to remove storage controller key for Local Key Management (LKM) configured. Supported function argument: controller_fqdd.

    rename_virtual_disk(script_examples='', virtual_disk_fqdd='', vd_name='')
        Function to rename virtual disk. Supported function arguments: virtual_disk_fqdd and vd_name.

    reset_bios_default_settings(script_examples='', reboot='')
        Function to reset BIOS to default settings. Supported function argument: reboot (supported_values: yes and no). Reboot server is needed to execute the operation. If you pass in no for reboot, operation is still scheduled and will execute on next server reboot.

    reset_controller(script_examples='', controller_fqdd='')
        Function to reset the storage controller which will delete all virtual disks. Supported function argument: controller_fqdd

    reset_iDRAC(script_examples='')
        Function to reset (reboot) iDRAC. This will only reboot the iDRAC, it will not reset any iDRAC settings to default values.

    return_iDRAC_script_session_details(script_examples='')
        Function to return iDRAC IP and iDRAC username session information that was captured by get_iDRAC_creds()

    secure_erase_disk(script_examples='', controller_fqdd='', disk_fqdd='')
        Function to secure erase (cryptographic erase) disk (HDD/SSD or NVMe type), supported function arguments: controller_fqdd and disk_fqdd. Note: Disk must not be part of a virtual disk for secure erase to pass.

    secure_virtual_disk(script_examples='', virtual_disk_fqdd='')
        Function to secure virtual disk (disks part of the virtual disk must be encryption capable (SED). Supported function argument: virtual disk FQDD.

    set_bios_attributes(script_examples='', attribute_name='', attribute_value='', reboot='')
        Function to set either one or multiple BIOS attributes. Supported function arguments: attribute_name, attribute_value and reboot(supported values are yes and no). Make sure to pass in attribute name exactly due to case senstive. Example: MemTest will pass but memtest will fail. If you want to configure multiple attributes, make sure to use a comma separator between each attribute name and attribute value. If needed, see examples for passing in multiple attribute names and values.

    set_controller_boot_virtual_disk(script_examples='', controller_fqdd='', virtual_disk_fqdd='')
        Function to set controller boot virtual disk. Supported function arguments: controller_fqdd and virtual_disk_fqdd

    set_iDRAC_attributes(script_examples='', group_name='', attribute_names='', attribute_values='')
        Function to set iDRAC, Lifecycle Controller or System attributes. Supported function arguments: group_name (supported values: idrac, lc and system), attribute_names (pass in one or more attribute name. If passing in multiple names use comma separator) and attribute values (make sure the values you pass in match the number of attribute names).

    set_iDRAC_script_session(script_examples='')
        Function to set iDRAC session used to execute all workflows for this session: pass in iDRAC IP, iDRAC username and iDRAC password. It will also prompt for SSL certificate verification for all Redfish calls and finally prompt to create X-auth token session. By creating X-auth token session, all Redfish calls executed will use this X-auth token session for authentication instead of username/password.

    set_idrac_default_settings(script_examples='', reset_type='')
        Function to reset iDRAC to default settings. Supported function argument: reset_type (supported values: "All"(Reset all iDRAC's configuration to default and reset user to shipping password value.), "ResetAllWithRootDefaults"(Reset all iDRAC's configuration to default and reset user to root\calvin) and "Default"(Reset all iDRAC's configuration to default and preserve user, network settings). Note: Make sure to pass in the exact case for the value. NOTE: If you execute this function to reset iDRAC to default settings, make sure to rerun IdracRedfishSupport.set_iDRAC_script_session() to set the session again.

    set_next_onetime_boot_device(script_examples='', get_supported_devices='', set_onetime_boot='', uefi_device_path='', get_uefi_device_paths='', reboot='')
        Function to either get supported onetime boot devices or set next onetime boot device. Supported function arguments: get_supported_devices (supported value: True), set_onetime_boot (pass in device string name and make sure to use exact case as returned from get_supported_devices), uefi_device_path (pass in uefi device target string), get_uefi_device_paths (supported value: True) and reboot (supported values: yes and no). If you do not reboot the now, onetime boot flag is still set and will boot to this device on next manual server reboot.

    set_server_power_state(script_examples='', power_state_value='')
        Function to change server power state to perform power operations. Supported function argument: power_state_value (supported values: execute "IdracRedfishSupport.get_current_server_power_state()" to get supported possible values)

    set_storage_controller_key(script_examples='', controller_fqdd='', key_id='')
        Function to set the storage controller key "enable encryption" for Local Key Management (LKM). Supported function arguments: controller_fqdd and key_id (unique string value). Once function is executed, it will prompt you to enter key passphrase to set (minimum length is 8 characters, must have at least 1 upper and 1 lowercase, 1 number and 1 special character. Refer to Dell PERC documentation for more information).

    supportassist_register(script_examples='', get_register_status='', register='', city='', companyname='', country='', email='', firstname='', lastname='', phonenumber='', state='', street='', zipcode='')
        Function to register SupportAssist, either get current register status or register SupportAssist. Supported function arguments: get_register_status (supported value: True), register (supported value: True), city, companyname, country, email (optional for register), firstname, lastname, phonenumber, state, street and zipcode.

    supportassist_schedule_auto_collection(script_examples='', get_supportassist_auto_collection_details='', clear_supportassist_auto_collection='', set_supportassist_auto_collection='', recurrence='', time='', dayofweek='', dayofmonth='')
        Function to either get, clear or set SupportAssist scheduled collection. Supported function arguments: script_examples (supported value: True), get_supportassist_auto_collection_details (supported value: True), clear_supportassist_auto_collection (supported value: True), set_supportassist_auto_collection_details (supported value: True), recurrence (supported values: Weekly, Monthly and Quarterly), time (supported time format: HH:MMAM/PM, example: "06:00PM"), dayofweek (supported values: Mon, Tue, Wed, Thu, Fri, Sat, Sun or * for all days of the week) and dayofmonth (supported values: 1 through 32 or L for last day or * for all days of the month).

    supportassist_status_accept_EULA(script_examples='', get_EULA_status='', accept_EULA='')
        Function to manage SupportAssist End User License Agreement (EULA). Supported function arguments: get_EULA_status (supported value: True) and accept_EULA (supported value: True)

    system_erase(script_examples='', get_supported_components='', erase_components='')
        Function to execute iDRAC system erase operation. System Erase feature allows you to reset BIOS or iDRAC to default settings, erase ISE drives, HDD drives, diags, driver pack, Lifecycle controller data, NVDIMMs, PERC NV cache or vFlash. Supported function arguments: get_supported_components (possible value: True), erase_components (pass in one or more multiple component values and make sure to pass in exact string case. If passing in multiple component values, use a comma separator. Once system erase job is completed, server will power off and reset the iDRAC, stay in off state once the iDRAC is back up.

    unassign_disk_hotspare(script_examples='', disk_fqdd='')
        Function to unassign disk hotspare. Supported function argument: disk_fqdd.

    unpack_and_attach_driver_pack(script_examples='', get_driver_packs='', get_attach_status='', attach_driver_pack='', detach_driver_pack='')
        Function to get either supported OS driver packs, attach status, attach driver pack or detach driver pack. Supported function arguments: get_driver_packs (supported value: True), get_attach_status (supported value: True), attach_driver_pack (supported value: Pass in OS driver pack string name) and detach_driver_pack (supported_value: True).
    
    insert_eject_virtual_media(script_examples="", get_attach_status="", insert_virtual_media="", eject_virtual_media="", image_path="")

    change_disk_state_virtualdisk(script_examples="", disk="", state=""):
    	Function to change the PD state of a disk part of a virtual disk, either set the disk to offline or bring back online. NOTE: Only RAID volumes which support parity are supported for this feature. Supported function arguments: disk (possible values: pass in disk FQDD) and state (possible values: offline and online).

    set_boot_virtualdisk(script_examples="", controller="", boot_vd=""):
    	Function to set boot virtual disk for storage controller. Supported function arguments: controller (pass in controller FQDD) and boot_vd (possible value: pass in virtual disk FQDD).

    blink_unblink_storage_device(script_examples="", blink="", unblink=""):
    	Function to blink or unblink either hard drive or virtual disk. Possible function arguments: blink (pass in drive or virtual disk FQDD string) and unblink (pass in drive or virtual disk FQDD string).

    cancel_check_consistency_virtual_disk(script_examples="", virtual_disk_fqdd=""):
    	Function to cancel check consistency operation running on a virtual disk. Supported function argument: virtual_disk_fqdd (pass in virtual disk FQDD).

    expand_virtualdisk(script_examples="", pdisks="", expand="", size=""):
        Function to expand storage virtual disk, either add a disk or expand current size. Supported function arguments: expand (pass in virtual disk FQDD), pdisks (possible value: Pass in disk(s) you want to add to the virtual disk. If you pass in multiple disk FQDDs use a comma separator between FQDDs.) and size (possible value: Pass in new VD size you want to expand to in MB).

    raidlevel_migration(script_examples="", pdisks="", migrate="", new_raid_level=""):
        Function to add additional hard drive(s) to the existing RAID Level to migrate to a new RAID level. Supported function arguments: migrate (pass in virtual disk FQDD), pdisks (possible value: Pass in disk(s) you want to add to the virtual disk. If you pass in multiple disk FQDDs use a comma separator between FQDDs.) and new_raid_level (possible values: RAID0, RAID1, RAID5, RAID6, RAID10, RAID50 and RAID60).

## Executing the module example:

1. At the python prompt, type "import IdracRedfishSupport" to load the module.

2. First step is to setup iDRAC session by typing "IdracRedfishSupport.set_iDRAC_script_session()". It will prompt you to enter:

- iDRAC IP address
- iDRAC username
- iDRAC password (password will not be echoed to the screen)
- Verify SSL certificate for all Redfish calls
- Create X-auth token session. Creating this session will execute all Redfish calls using X-auth instead of username/password.

3. Once iDRAC session has now been established, you can now start to execute workflow functions. See "Supported Module Functions" section for all supported function workflows. 

4. If needed, each method has doc help along with script executing examples.

## Example of executing module functions:

C:\>python
Python 3.10.2 (tags/v3.10.2:a58ebcc, Jan 17 2022, 14:12:15) [MSC v.1929 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license" for more information.
>>> import IdracRedfishSupport
>>> IdracRedfishSupport.set_iDRAC_script_session()
- Enter iDRAC IP: 192.168.0.120
- Enter iDRAC username: root
- Enter iDRAC root password:
- Verify SSL certificate, pass in True to verify or False to ignore: false
- Create iDRAC X-auth token session? Pass in "y" for yes or "n" for no. Creating iDRAC X-auth token session, all Redfish commands will be executed using this X-auth token for auth instead of username/password: n
>>>
>>>
>>> IdracRedfishSupport.get_storage_controllers()

- Server controller(s) detected -

RAID.SL.3-1
AHCI.Embedded.2-1
AHCI.SL.6-1
AHCI.Embedded.1-1

>>> IdracRedfishSupport.get_virtual_disks(controller_fqdd="RAID.SL.3-1")

- Volume(s) detected for RAID.SL.3-1 controller -

Disk.Virtual.0:RAID.SL.3-1, Volume type: Mirrored, RAID type: RAID1
Disk.Virtual.1:RAID.SL.3-1, Volume type: NonRedundant, RAID type: RAID0

>>> IdracRedfishSupport.delete_virtual_disk.__doc__
'Function to delete storage controller virtual disk. Supported function argument: virtual_disk_fqdd (pass in virtual disk FQDD string)'

>>> IdracRedfishSupport.delete_virtual_disk(script_examples=True)

- IdracRedfishSupport.delete_virtual_disk(virtual_disk_fqdd='Disk.Virtual.1:RAID.Mezzanine.1-1'), this example will delete VD 1 for controller RAID.Mezzanine.1-1

>>> IdracRedfishSupport.delete_virtual_disk(virtual_disk_fqdd="Disk.Virtual.1:RAID.SL.3-1")

- PASS: DELETE command passed to delete "Disk.Virtual.1:RAID.SL.3-1" virtual disk, status code 202 returned

- PASS, "realtime" JID_485075604808 jid successfully created to delete virtual disk
- INFO, realtime config job detected, no reboot needed to execute storage operation
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."
- INFO, job status not completed, current status: "Job in progress."

--- PASS, Final Detailed Job Status Results ---

@odata.context: /redfish/v1/$metadata#DellJob.DellJob
@odata.id: /redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/JID_485075604808
@odata.type: #DellJob.v1_2_0.DellJob
ActualRunningStartTime: 2022-03-28T17:46:01
ActualRunningStopTime: 2022-03-28T17:47:22
CompletionTime: 2022-03-28T17:47:22
Description: Job Instance
EndTime: TIME_NA
Id: JID_485075604808
JobState: Completed
JobType: RealTimeNoRebootConfiguration
Message: Job completed successfully.
MessageArgs: []
MessageArgs@odata.count: 0
MessageId: PR19
Name: Configure: RAID.SL.3-1
PercentComplete: 100
StartTime: 2022-03-28T17:46:00
TargetSettingsURI: None
>>>
>>> IdracRedfishSupport.insert_eject_virtual_media(insert_virtual_media="cd", image_path="https://3.137.219.52/centos/7/isos/x86_64/CentOS-7-live-GNOME-x86_64.iso")

 - INFO, insert(attached) "CD" virtual media device "https://3.137.219.52/centos/7/isos/x86_64/CentOS-7-live-GNOME-x86_64.iso"

- PASS, POST command passed to successfully insert(attached) CD media, status code 204 returned
>>> IdracRedfishSupport.insert_eject_virtual_media(eject_virtual_media="cd")

- PASS, POST command passed to successfully eject(detach) CD media, status code 204 returned
>>>