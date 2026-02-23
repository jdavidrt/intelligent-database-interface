# Makefile for building llama.cpp server from source
# Run `make` from the sandbox/ directory to build everything.

LLAMA_DIR = llama.cpp
BUILD_DIR  = $(LLAMA_DIR)/build

.PHONY: all build clone clean

## Default target: clone (if needed) and build
all: clone build

## Clone the llama.cpp source repository (skips if already cloned)
clone:
	@if not exist "$(LLAMA_DIR)\.git" ( \
		echo Cloning llama.cpp source... && \
		git clone https://github.com/ggml-org/llama.cpp.git $(LLAMA_DIR) \
	) else ( \
		echo llama.cpp already cloned, skipping. \
	)

## Configure and build the llama-server binary using CMake
build:
	cmake -S $(LLAMA_DIR) -B $(BUILD_DIR) -DLLAMA_BUILD_SERVER=ON
	cmake --build $(BUILD_DIR) --config Release

## Clean the build artifacts
clean:
	cmake --build $(BUILD_DIR) --target clean
