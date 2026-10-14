cmake_minimum_required(VERSION 3.13)

# Default to the Pico 2. Build for the original Pico with -DPICO_BOARD=pico
if(NOT DEFINED PICO_BOARD)
    set(PICO_BOARD pico2)
endif()

include(pico_sdk_import.cmake)
project(squeak_tap C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

add_executable(squeak_tap main.c usb_descriptors.c)
pico_generate_pio_header(squeak_tap ${CMAKE_CURRENT_LIST_DIR}/sampler.pio)
target_include_directories(squeak_tap PRIVATE ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(squeak_tap PRIVATE
    pico_stdlib
    pico_multicore
    pico_unique_id
    hardware_pio
    tinyusb_device)

# Run entirely from RAM so flash access never stalls the sampling core.
pico_set_binary_type(squeak_tap copy_to_ram)
pico_add_extra_outputs(squeak_tap)
