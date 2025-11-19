set(COVERAGETOOL_PY
    ${CMAKE_CURRENT_SOURCE_DIR}/flow/coveragetool/coveragetool.py)

add_custom_target(coveragetool
                  DEPENDS ${COVERAGETOOL_PY})
set(coveragetool_exe "${Python3_EXECUTABLE}" "${COVERAGETOOL_PY}")
