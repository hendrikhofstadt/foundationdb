set(TRACELOGHELPER_SRCS
    ${CMAKE_CURRENT_SOURCE_DIR}/__init__.py
    ${CMAKE_CURRENT_SOURCE_DIR}/event.py
    ${CMAKE_CURRENT_SOURCE_DIR}/json_parser.py
    ${CMAKE_CURRENT_SOURCE_DIR}/trace_log_util.py
    ${CMAKE_CURRENT_SOURCE_DIR}/xml_parser.py
)

# TraceLogHelper is now a Python package - no compilation needed
add_custom_target(TraceLogHelper DEPENDS ${TRACELOGHELPER_SRCS})

# Set path to the Python package for other targets that might need it
set(TraceLogHelperPath "${CMAKE_CURRENT_SOURCE_DIR}")
