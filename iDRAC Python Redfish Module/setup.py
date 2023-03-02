from setuptools import setup, find_packages
import codecs
import os

define_path = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(define_path, "README.txt"), encoding="utf-8") as x:
    long_description = "\n" + x.read()

DESCRIPTION = "iDRAC Redfish API support for multiple iDRAC workflows."
LONG_DESCRIPTION = "Python module for iDRAC Redfish support to allow the user to perform multiple workflows. This module can be imported from python prompt to start an interactive session with the iDRAC to perform multiple operations. Some workflow examples include configuration changes, firmware updates, exporting logs and SupportAssist collection. See module function section below for all supported workflows."

# Setting up
setup(
        name="IdracRedfishSupport", 
        version="0.0.8",
        license="GPLv2",
        author="Texas Roemer",
        author_email="texas_roemer@dell.com",
        description=DESCRIPTION,
        long_description_content_type="text/markdown",
        long_description=long_description,
        packages=find_packages(),
        url="https://github.com/dell/iDRAC-Redfish-Scripting",
        install_requires=["requests",],
        keywords=["python", "Redfish", "IDRAC"],
        scripts=["AssignHotSpareREDFISH.py","BiosChangePasswordREDFISH.py","BiosDeviceRecoveryREDFISH.py",
                 "BiosResetToDefaultsREDFISH.py","BlinkUnBlinkTargetREDFISH.py","BootToNetworkIsoOsdREDFISH.py",
                 "CancelCheckConsistencyVirtualDiskREDFISH.py","ChangeBiosBootOrderREDFISH.py","ChangeIdracUserPasswordREDFISH.py",
                 "ChangePdStateREDFISH.py","ChangeVirtualDiskAttributesREDFISH.py","CheckConsistencyVirtualDiskREDFISH.py",
                 "ClearForeignConfigREDFISH.py","ConvertToNonRAIDREDFISH.py","ConvertToRAIDREDFISH.py",
                 "CreateDeleteIdracUsersREDFISH.py","CreateServerRebootJobREDFISH.py","CreateVirtualDiskREDFISH.py",
                 "CreateXAuthTokenSessionREDFISH.py","DeleteFirmwarePackageREDFISH.py","DeleteJobQueueREDFISH.py",
                 "DeleteVirtualDiskREDFISH.py","DellSwitchConnectionCollectionREDFISH.py","DeviceFirmwareMultipartUploadREDFISH.py",
                 "DeviceFirmwareRollbackMultipleDevicesREDFISH.py","DeviceFirmwareRollbackREDFISH.py","DeviceFirmwareSimpleUpdateCheckVersionREDFISH.py",
                 "DeviceFirmwareSimpleUpdateREDFISH.py","DeviceFirmwareSimpleUpdateTransferProtocolREDFISH.py","EnableDisableBiosBootOrderDevicesREDFISH.py",
                 "ExportClearSerialDataLogsREDFISH.py","ExportFactoryConfigurationREDFISH.py","ExportHWInventoryREDFISH.py",
                 "ExportImportSSLCertificateREDFISH.py","ExportLCLogREDFISH.py","ExportServerScreenShotREDFISH.py",
                 "ExportSystemConfigurationLocalREDFISH.py","ExportSystemConfigurationNetworkShareREDFISH.py","ExportThermalHistoryREDFISH.py",
                 "ExportVideoLogREDFISH.py","FirmwareUpdateLocalRepoREDFISH.py","GenerateCsrREDFISH.py",
                 "GetAssemblyInventoryREDFISH.py","GetDHSDisksREDFISH.py","GetDeleteiDRACSessionsREDFISH.py",
                 "GetDiskOperationREDFISH.py","GetEthernetInterfacesREDFISH.py","GetFirmwareInventoryREDFISH.py",
                 "GetIdracLcLogsREDFISH.py","GetIdracLcSystemAttributesREDFISH.py","GetIdracMessageRegistryREDFISH.py",
                 "GetIdracSelLogsREDFISH.py","GetIdracServerSlotInformationREDFISH.py","GetIdracServiceRootDetailsNoCredsREDFISH.py",
                 "GetNvDimmInventoryREDFISH.py","GetOSInformationREDFISH.py","GetOSNetworkInformationREDFISH.py",
                 "GetPCIeDeviceInventoryREDFISH.py","GetRAIDLevelsREDFISH.py","GetRemoteServicesAPIStatusREDFISH.py",
                 "GetSchemaPrivilegesREDFISH.py","GetSetBiosAttributesREDFISH.py","GetSetOemNetworkDevicePropertiesREDFISH.py",
                 "GetSetPowerStateREDFISH.py","GetStorageInventoryREDFISH.py","GetSystemHWInventoryREDFISH.py",
                 "IdracHardeningREDFISH.py","IdracLicenseManagementDmtfREDFISH.py","IdracLicenseManagementOemREDFISH.py",
                 "IdracRecurringJobOemREDFISH.py","IdracResetToDefaultsREDFISH.py","ImportForeignConfigREDFISH.py",
                 "ImportSystemConfigurationLocalFilenameREDFISH.py","ImportSystemConfigurationLocalREDFISH.py","ImportSystemConfigurationNetworkSharePreviewREDFISH.py",
                 "ImportSystemConfigurationNetworkShareREDFISH.py","ImportSystemConfigurationPreviewLocalFilenameREDFISH.py","InitializeVirtualDiskREDFISH.py",
                 "InsertEjectVirtualMediaREDFISH.py","InsertLclogCommentREDFISH.py","InstallFromRepositoryREDFISH.py",
                 "LCWipeREDFISH.py","LaunchIdracRemoteKvmHtmlSessionREDFISH.py","LockVirtualDiskREDFISH.py",
                 "ManageIdracTimeREDFISH.py","PrepareToRemoveREDFISH.py","RaidLevelMigrationREDFISH.py",
                 "ReKeyREDFISH.py","RemoveControllerKeyREDFISH.py","RenameVdREDFISH.py",
                 "ReplaceCsrREDFISH.py","ResetConfigStorageREDFISH.py","ResetIdracREDFISH.py",
                 "ResetSslConfigREDFISH.py","RunDiagnosticsREDFISH.py","SecureBootCertificatesDbxREDFISH.py",
                 "SecureBootResetKeysREDFISH.py","SecureEraseDevicesREDFISH.py","SensorCollectionREDFISH.py",
                 "ServerVirtualAcPowerCycleREDFISH.py","SetBiosDefaultSettingsREDFISH.py","SetBootVdREDFISH.py",
                 "SetChassisIndicatorLedREDFISH.py","SetControllerKeyREDFISH.py","SetIdracLcSystemAttributesREDFISH.py",
                 "SetIdracSensorSystemBoardInletTemp.py","SetNetworkDevicePropertiesREDFISH.py","SetNextOneTimeBootDeviceREDFISH.py",
                 "SetNextOneTimeBootVirtualMediaDeviceOemREDFISH.py","SubscriptionManagementREDFISH.py","SupportAssistCollectionAutoCollectScheduleREDFISH.py",
                 "SupportAssistCollectionLocalREDFISH.py","SupportAssistCollectionNetworkShareREDFISH.py","SystemEraseREDFISH.py",
                 "TestNetworkShareREDFISH.py","UnassignHotSpareREDFISH.py","UnpackAndAttachOsdREDFISH.py","VirtualDiskExpansionREDFISH.py"]
)
