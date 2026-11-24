# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location
# (note this can come from environment, CMake cache etc)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico2_w CACHE STRING "Board type")

# Optional log categories. Both are off by default so a normal build stays quiet.
option(ENABLE_USB_LOGGING "Log USB device events and HID report traffic" OFF)
option(ENABLE_HEARTBEAT_LOGS "Log a periodic Core 0 heartbeat" OFF)
option(LG_ENABLE_HID "Translate the captured MR25GA buttons and wheel to USB HID" OFF)

# Baud rate of the log UART. Lower it for a receiver that cannot keep up, such
# as a bit-banged software UART on an AVR.
set(UART_BAUD_RATE 115200 CACHE STRING "Baud rate of the log UART")

# Pull in Raspberry Pi Pico SDK (must be before project)
include(pico_sdk_import.cmake)

project(picow_ble_usb_hid_bridge C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()

# Optional publication path sanitization, preserving the SDK's CPU/ABI flags.
# Applied to all sources in this build, including SDK interface sources.
if(LG_BUILD_PATH_FLAGS)
    foreach(LANG C CXX ASM)
        set(CMAKE_${LANG}_FLAGS "${CMAKE_${LANG}_FLAGS} ${LG_BUILD_PATH_FLAGS}")
    endforeach()
endif()

# Replace only this build graph's HID client; never edit the shared SDK.
file(SHA256 "${PICO_BTSTACK_PATH}/src/ble/gatt-service/hids_client.c" LG_HIDS_UPSTREAM_SHA)
if(NOT LG_HIDS_UPSTREAM_SHA STREQUAL "b06ef344f0c22dfe795be82a2b2d8756ecfa18111fcbf497a945f8c71d7e93a7")
    message(FATAL_ERROR "HID cache extension requires reviewed pinned BTstack hids_client source")
endif()
get_target_property(LG_BLE_SOURCES pico_btstack_ble INTERFACE_SOURCES)
list(FILTER LG_BLE_SOURCES EXCLUDE REGEX "/gatt-service/hids_client\\.c$")
set_property(TARGET pico_btstack_ble PROPERTY INTERFACE_SOURCES "${LG_BLE_SOURCES}")


add_compile_options(-Wall
        -Wno-format          # int != int32_t as far as the compiler is concerned because gcc has int32_t as long int
        -Wno-unused-function # we have some for the docs that aren't called
        -Wno-maybe-uninitialized
        )

# Add executable.  
add_executable(picow_ble_usb_hid_bridge
    diagnostic.c
    bridge_hid.c
    main.c
    usb_descriptors.c
    hog_host_demo.c
    bt_example_common.c
    Common.c
    host_usb.c
    reconnect_probe.c
    hid_reconnect.c
    hids_client_cached.c
    )  
target_link_libraries(picow_ble_usb_hid_bridge
    pico_stdlib
    pico_multicore
    pico_flash # flash_safe_execute_core_init(), used in main()
    hardware_sync
    pico_unique_id
    pico_rand
    tinyusb_device
    tinyusb_board
    pico_btstack_ble
    pico_btstack_cyw43
    pico_btstack_flash_bank
    pico_cyw43_arch_none
    )   
target_include_directories(picow_ble_usb_hid_bridge PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    )
target_compile_definitions(picow_ble_usb_hid_bridge PRIVATE 
    PICO_STACK_SIZE=4096
    PICO_CORE1_STACK_SIZE=4096
    CYW43_LWIP=0
    LG_ENABLE_HID=$<BOOL:${LG_ENABLE_HID}>
    PICO_DEFAULT_UART_BAUD_RATE=${UART_BAUD_RATE}
    )    
    
if(ENABLE_USB_LOGGING)
    target_compile_definitions(${PROJECT_NAME} PRIVATE ENABLE_USB_LOGGING=1)
endif()    
    
if(ENABLE_HEARTBEAT_LOGS)
    target_compile_definitions(
        ${PROJECT_NAME}
        PRIVATE ENABLE_HEARTBEAT_LOGS=1
    )
endif()    
    
pico_btstack_make_gatt_header(picow_ble_usb_hid_bridge PRIVATE 
    ${CMAKE_CURRENT_SOURCE_DIR}/hog_host_demo.gatt
    )

# disable usb output, enable uart output
pico_enable_stdio_usb(picow_ble_usb_hid_bridge 0)
pico_enable_stdio_uart(picow_ble_usb_hid_bridge 0)

# create map/bin/hex/uf2 file etc.
pico_add_extra_outputs(picow_ble_usb_hid_bridge)

file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/../../VERSION" LG_BRIDGE_VERSION LIMIT_COUNT 1)
target_compile_definitions(${PROJECT_NAME} PRIVATE LG_BRIDGE_VERSION="${LG_BRIDGE_VERSION}")
if(LG_ENABLE_HID)
    pico_set_program_name(${PROJECT_NAME} "lg-magic-pico2w-bridge")
    pico_set_program_version(${PROJECT_NAME} "${LG_BRIDGE_VERSION}-airmouse")
else()
    pico_set_program_name(${PROJECT_NAME} "lg-magic-pico2w-diagnostic")
    pico_set_program_version(${PROJECT_NAME} "${LG_BRIDGE_VERSION}-diagnostic")
endif()
