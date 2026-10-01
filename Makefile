.PHONY: help demo demo-emulated

help:
	@echo "Targets:"
	@echo "  demo           Run Tusk via docker compose"
	@echo "  demo-emulated  Run the emulator shell against a scripted transcript"

demo:
	docker compose up

demo-emulated:
	docker compose run --rm --no-deps -e TUSK_SHELLS=emulator \
		-e TUSK_TRANSCRIPT=demos/coding_session_emulated.txt \
		-e TUSK_UTTERANCE_PAUSE=0 \
		-v ./demos/editor_emulator:/app/adapters/editor_emulator:ro \
		tusk python main.py
