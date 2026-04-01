[app]
title = OperacionesTrebol
package.name = operaciones_trebol
package.domain = com.trebol
source.dir = .
source.include_exts = py,kv,json,png,jpg,ttf
version = 0.1.0
requirements = python3,kivy==2.3.0,kivymd==1.2.0,requests,sqlite3
orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
