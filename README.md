# The **B**ehavior **E**nsemble and **N**eural **T**rajectory **O**bservatory (Bento)

## Changes in this branch (`v0.2.1-beta-edits`, thugeun fork)

Based on v0.2.1-beta. Tested on Windows 11 with Python 3.6 / PySide2 5.15.2.

### Mouse editing of annotation bouts (annotations view)
| Action | Result |
|---|---|
| Click a bout | Select it (black outline). Click empty space or press `Esc` to deselect. When bouts overlap, the shortest one is picked. |
| Drag the start/end edge of the selected bout | Move that edge (cursor turns to `↔` near an edge; hatched preview while dragging). On release, overlapping bouts of the same behavior are merged and the video jumps to the edited edge. |
| Double-click the start/end edge of the selected bout | Reopen that edge as a *pending bout*: the hatched region follows the current time exactly like a hot-key annotation. Confirm with the behavior's hot key **or** a double-click on the timeline at the desired time. `Esc` or another behavior's hot key cancels and restores the original bout. |
| Double-click on the timeline while a pending bout exists | Commit the pending bout at the clicked time (same as pressing its hot key there). |
| `Delete` | Delete the selected bout. (`Backspace` keeps its original delete-hot-key meaning.) |

Dragging anywhere that is not a selected bout's edge still scrubs time as before.

### Time navigation
- **Mouse wheel** scrolls time anywhere over the main window: 1 frame per notch, `Shift` = 10 frames, `Ctrl` = 30 frames (constants `WHEEL_FRAMES*` in `src/bento.py`). Trackpad horizontal swipe still works.
- **Arrow keys** always scroll time. Buttons and the channel combo box no longer take keyboard focus, so clicking a button does not turn the arrow keys into button-focus navigation.

### Behaviors window: Save now actually persists on Windows
- Bug: `save()` wrote `os.linesep` into a text-mode file, producing `\r\r\n` on Windows. `load()` then failed on the resulting blank lines and Bento silently fell back to the default `color_profiles.txt`, so edited hot keys were lost on restart.
- Fix: lines end with `\n`; blank lines are skipped on load.
- `active` and `visible` flags are now saved too, as two optional trailing `0/1` fields
  (`hot_key name r g b active visible`). Old 5-field files still load.
- Profile location: `~/.bento/color_profiles.txt`.

---

Bento is a tool for organizing, visualizing, and analyzing multimodal neuroscience datasets.

An earlier, Matlab-based version of Bento is available [here](https://github.com/neuroethology/bentoMAT).

## New In This Release

### Version 0.2.0-beta
#### Added Features
- A plug-in interface to support import and display of pose data
- A pose plug-in for MARS format mouse pose data
- A pose plug-in for DeepLabCut format generic and MARS-style mouse pose data (*.h5, or *.csv)
- "Parula" color table for display of neural heatmap data
- Annotations can now be applied from the neural viewer window

#### Bugs Fixed
- On initial startup when no Investigators yet exist, v0.1.0-beta would prompt for the selection of an Investigator anyway.
With this release, it takes you to the "Add Investigators" dialog instead.
- The vertical scaling of annotations has been fixed.
## Features

## Getting Started

- Please look for the installation instructions at [Installation Instructions](https://github.com/neuroethology/bento/blob/main/documentation/installation.md)
- Please look for the detailed step by step instructions at [Tutorial](https://github.com/neuroethology/bento/blob/main/documentation/tutorial.md)

## Citation

## License

## Contact
