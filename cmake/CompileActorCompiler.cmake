find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(ACTORCOMPILER_PY_SRCS
  ${CMAKE_CURRENT_SOURCE_DIR}/flow/actorcompiler_py/__main__.py
  ${CMAKE_CURRENT_SOURCE_DIR}/flow/actorcompiler_py/errors.py
  ${CMAKE_CURRENT_SOURCE_DIR}/flow/actorcompiler_py/actor_parser.py
  ${CMAKE_CURRENT_SOURCE_DIR}/flow/actorcompiler_py/actor_compiler.py)

add_custom_target(actorcompiler DEPENDS ${ACTORCOMPILER_PY_SRCS})

set(ACTORCOMPILER_COMMAND
  ${Python3_EXECUTABLE} -m flow.actorcompiler_py
  CACHE INTERNAL "Command to run the actor compiler")
