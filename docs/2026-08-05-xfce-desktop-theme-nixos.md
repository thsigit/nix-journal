# Xfce Desktop Theme On NixOS

**Date:** 2026-08-05  
**Author:** Codebot  
**Topic:** NixOS, Xfce, sddm, homelab, desktop, theme  

---

## 1. Objective

Configure proper Xfce desktop for workstation profile after repository restructuring.

## 2. Background

After making /srv/repo/nix-lab active and /srv/repo/nix-config stable, workstation profile needed Xfce configuration. Previous setup minimal: default theme, single panel, no customization.

## 3. Problem

No customized desktop environment for workstation profile.

## 4. Work Performed

### 4.1 Theme and Appearance
- Window manager: Adwaita-dark
- GTK theme: Adwaita-dark
- Icon theme: Papirus-Dark
- Cursor: Bibata-Modern-Ice (size 24)
- Fonts: Sans 10, Monospace 10

### 4.2 Panel Layout (Dual Vertical)
| Panel | Position | Plugins |
|-------|----------|---------|
| Panel 1 | Top-right (vertical) | Clock, tasklist, actions |
| Panel 2 | Bottom-left (vertical) | Whisker menu, systray |

Both panels: mode=vertical (mode=1), size=48px, position-locked=true, background=transparent (system theme), flat buttons=enabled.

### 4.3 Wallpaper
Desktop background set to assets/wallpaper.jpg via xfconf-query, applied to all screens/monitors through autostart script.

### 4.4 Display Manager
- SDDM with sddm-astronaut theme
- Auto-login enabled for user sigit
- LightDM disabled

### 4.5 Desktop Behavior
- Compositing: enabled
- Frame shadows: enabled
- Desktop icons: disabled (style=0)
- Screen blanking: disabled via power manager

### 4.6 Implementation
Configuration in profiles/workstation/xfce4.nix. Xfce panel plugin IDs dynamically assigned at runtime, so setup uses XDG autostart script rather than static xfconf values:
```nix
environment.etc."xdg/autostart/xfce-theme-setup.desktop".text = ''
  [Desktop Entry]
  Type=Application
  Name=XFCE Theme Setup
  Exec=${xfce-setup}
  OnlyShowIn=XFCE;
  X-GNOME-Autostart-enabled=true;
  NoDisplay=true;
'';
```
Script runs xfconf-query to configure themes, panels, plugins, wallpaper on each login. Plugin discovery dynamic -- script checks if panels already have plugins configured and only sets up on first boot.

### 4.7 Packages Added
- xfce4-whiskermenu-plugin: start menu replacement
- bibata-cursors: cursor theme
- papirus-icon-theme: icon theme
- arc-theme: fallback GTK theme

### 4.8 Excluded Packages
- mousepad: text editor (not needed)
- ristretto: image viewer (not needed)

### 4.9 Desktop Start Gotcha
After sudo nixos-rebuild switch --flake .#workstation, desktop doesn't auto-start. Expected -- nixos-rebuild switch updates system config but doesn't restart display managers.

Solution:
```bash
# Option 1: Start SDDM manually (from TTY)
sudo systemctl start display-manager
# Option 2: Reboot
sudo reboot
```
Display manager was already inactive before rebuild. SDDM starts on boot, not rebuild. With auto-login, starting SDDM drops directly into XFCE.

### 4.10 File Structure
```
profiles/workstation/
|-- default.nix      # imports core, network, storage, security, etc.
|-- xfce4.nix        # desktop theme, panels, SDDM
|-- packages.nix     # workstation-specific packages
```

### 4.11 Verification
After starting SDDM:
- Whisker menu appears bottom-left
- Clock and tasklist appear top-right
- Dark theme applied to all windows
- Wallpaper displayed on all workspaces
- Cursor is Bibata-Modern-Ice

## 5. Diagnosis

Xfce panel plugin IDs require runtime discovery. Autostart script handles dynamic configuration.

## 6. Preliminary Assessment

Desktop configuration declarative and reproducible. Auto-login + SDDM provides seamless entry.

## 7. Solution Summary

Xfce configured with dark theme, dual vertical panels, SDDM auto-login, custom wallpaper. Implementation via autostart script for dynamic plugin IDs.

## 8. Verification Plan

Reboot workstation. Verify all theme elements, panels, auto-login functional.

## 9. Pending Actions

None.

## 10. Recommendations

Use autostart scripts for dynamic Xfce configuration. Keep package lists minimal. Document display manager restart requirement after rebuild.
