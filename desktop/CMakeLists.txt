cmake_minimum_required(VERSION 3.21)
project(FeldmarschallDesk VERSION 1.0 LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
find_package(Qt6 6.4 REQUIRED COMPONENTS Core Gui Widgets Sql)
find_package(OpenMP REQUIRED COMPONENTS CXX)
find_package(ZLIB REQUIRED)
find_package(Python3 REQUIRED COMPONENTS Interpreter)

add_library(classic STATIC classic.cpp)
target_link_libraries(classic PUBLIC Qt6::Core)
target_include_directories(classic PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_compile_options(classic PRIVATE -Wall -Wextra)

add_executable(feldmarschall-tournament-worker worker.cpp)
target_link_libraries(feldmarschall-tournament-worker PRIVATE classic OpenMP::OpenMP_CXX)
target_compile_options(feldmarschall-tournament-worker PRIVATE -Wall -Wextra)
set_property(TARGET feldmarschall-tournament-worker APPEND PROPERTY LINK_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/../tools/record_native_worker.py
    ${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.txt)
add_custom_command(TARGET feldmarschall-tournament-worker POST_BUILD
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/record_native_worker.py
        ${CMAKE_CURRENT_SOURCE_DIR}/.. $<TARGET_FILE:feldmarschall-tournament-worker>
        ${CMAKE_CXX_COMPILER} ${CMAKE_CURRENT_BINARY_DIR}/compile_commands.json
    VERBATIM)

set(art ${CMAKE_CURRENT_BINARY_DIR}/art)
add_custom_command(OUTPUT ${art}/assets.qrc
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/../tools/build_desktop_assets.py ${art}
    DEPENDS ../tools/build_desktop_assets.py ../assets/scripts/pieces.py
            ../assets/scripts/terrain.py ../assets/scripts/palette.py
            ../assets/scripts/layout.py ../assets/scripts/bitmap_font.py
            ../assets/pieces/prussian.png ../assets/font/kakuro-ui.png
    VERBATIM)
set_source_files_properties(${art}/assets.qrc PROPERTIES GENERATED TRUE)
set(CMAKE_AUTORCC ON)
add_executable(feldmarschall-desk main.cpp desk.cpp desk.h ${art}/assets.qrc)
target_link_libraries(feldmarschall-desk PRIVATE classic Qt6::Widgets Qt6::Sql ZLIB::ZLIB)
target_compile_definitions(feldmarschall-desk PRIVATE FMT_PROJECT_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/..")
target_compile_options(feldmarschall-desk PRIVATE -Wall -Wextra)
add_dependencies(feldmarschall-desk feldmarschall-tournament-worker)

enable_testing()
add_test(NAME native-tournaments COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/../tools/test_native_desktop.py
    --bin-dir ${CMAKE_CURRENT_BINARY_DIR})
set_tests_properties(native-tournaments PROPERTIES TIMEOUT 120 ENVIRONMENT "QT_QPA_PLATFORM=offscreen")
