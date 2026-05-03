# Razor Enhanced Script Refactor & Overhaul Plan

## Goals
- Improve reliability and maintainability of all scripts
- Standardize logging, error handling, and user feedback
- Ensure robust item movement and targeting logic
- Modularize common helpers/utilities
- Add configuration and documentation for each script

## General Refactor Steps
1. **Audit All Scripts**
   - List all scripts and their main functions
   - Identify duplicated logic (e.g., item moving, logging, targeting)
   - Any logging functionality should revolve around a debug variable and mainly used to pass data back from the game to github copilot agents.
2. **Extract Common Utilities**
   - Logging helpers
   - Item movement with verification
   - Targeting and prompt helpers
   - Corpse/loot scanning
3. **Standardize Script Structure**
   - Consistent entry point (`main()`)
   - Clear configuration section
   - Inline or external documentation
   - Consistent error handling and logging
4. **Improve Item Movement Logic**
   - Always move by serial when possible
   - Check return values and verify item location after move
   - Handle failures gracefully (retry, log, skip)
5. **Enhance User Feedback**
   - Use color-coded messages
   - Clear error/warning/info logs
   - Prompt user for input when needed
6. **Testing & Validation**
   - Test each script in-game for edge cases
   - Add debug mode for verbose output
   - Document known issues and limitations
7. **Ensure Script runs on any system.
    - Ensure none of the variables or code contain static references to a file or folder
    - Make the script stable on any Razor Client

## Overhaul Ideas
- Create a `utils.py` for shared helpers
- Add a config file or section for user-tunable settings
- Add a README for each major script
- Consider a script loader/manager for easier use
- Add more robust corpse/item filtering (e.g., ignore player corpses, filter by loot type)
- Add support for multiple pack animals or containers

## Next Steps
1. List all scripts and their main purpose
2. Identify top pain points and bugs
3. Prioritize scripts for refactor (start with most used or most broken)
4. Begin extracting utilities and refactoring scripts one by one

---

_This plan is a living document. Update as you discover new issues or ideas during the refactor process.

Refactor. Many of these scripts were adopted from a long time ago and may not be working. With the exception of the util folders we want to put them in these respective folders:

--Utils
    -- misc folders at the root of the directory used for all helpers and game info.
--Verified
    -- only scripts with a done status are eligible for this currently none are.
--In Progress
    -- any files created or modified since the date that all of the content in this directory were added.
--Untested
    -- Remaining scripts.

_
