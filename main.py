"""
PINGIPOOL Backend v5 - HYBRID 3D SYSTEM
Sistema ibrido con componenti 3D pre-definiti + AI Assembly
"""

import os
import sys
import json
import httpx
import asyncio
import re
import math
import uuid
import traceback
from datetime import datetime

# Fix Windows cp1252 console encoding for emoji
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="PINGIPOOL J.A.R.V.I.S. Backend v5 HYBRID")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
FAL_API_KEY = os.getenv("FAL_API_KEY", "")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# Modello Gemini
GEMINI_MODEL = "gemini-3.1-pro-preview"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# Storage
shared_projects = {}

print(f"🔑 OPENAI: {'✅' if OPENAI_API_KEY else '❌'}")
print(f"🔑 GEMINI: {'✅' if GEMINI_API_KEY else '❌'}")
print(f"🔑 ANTHROPIC: {'✅ ' + ANTHROPIC_API_KEY[:12] + '...' if ANTHROPIC_API_KEY else '❌'}")
print(f"🤖 Model: {GEMINI_MODEL}")
print(f"🔧 System: HYBRID 3D v5")


# ═══════════════════════════════════════════════════════════════════════════
# 3D COMPONENT LIBRARY - MATEMATICAMENTE PERFETTI
# ═══════════════════════════════════════════════════════════════════════════

class Component3D:
    """Generatore di componenti 3D wireframe"""
    
    @staticmethod
    def cube(x: float, y: float, z: float, w: float, h: float, d: float) -> List[Dict]:
        """
        Genera un cubo/box wireframe
        x,y,z = centro del cubo
        w,h,d = larghezza, altezza, profondità
        Ritorna 12 linee (bordi del cubo)
        """
        hw, hh, hd = w/2, h/2, d/2
        
        # 8 vertici
        v = [
            [x-hw, y-hh, z-hd],  # 0: back-bottom-left
            [x+hw, y-hh, z-hd],  # 1: back-bottom-right
            [x+hw, y+hh, z-hd],  # 2: back-top-right
            [x-hw, y+hh, z-hd],  # 3: back-top-left
            [x-hw, y-hh, z+hd],  # 4: front-bottom-left
            [x+hw, y-hh, z+hd],  # 5: front-bottom-right
            [x+hw, y+hh, z+hd],  # 6: front-top-right
            [x-hw, y+hh, z+hd],  # 7: front-top-left
        ]
        
        # 12 bordi
        edges = [
            (0,1), (1,2), (2,3), (3,0),  # back face
            (4,5), (5,6), (6,7), (7,4),  # front face
            (0,4), (1,5), (2,6), (3,7),  # connecting edges
        ]
        
        return [{"start": v[a], "end": v[b]} for a, b in edges]
    
    @staticmethod
    def cylinder(x: float, y: float, z: float, radius: float, height: float, segments: int = 16) -> List[Dict]:
        """
        Genera un cilindro wireframe verticale
        x,y,z = centro della base
        Ritorna cerchio base + cerchio top + linee verticali
        """
        lines = []
        
        # Cerchio base (y = y)
        for i in range(segments):
            a1 = (i / segments) * 2 * math.pi
            a2 = ((i + 1) / segments) * 2 * math.pi
            lines.append({
                "start": [x + radius * math.cos(a1), y, z + radius * math.sin(a1)],
                "end": [x + radius * math.cos(a2), y, z + radius * math.sin(a2)]
            })
        
        # Cerchio top (y = y + height)
        for i in range(segments):
            a1 = (i / segments) * 2 * math.pi
            a2 = ((i + 1) / segments) * 2 * math.pi
            lines.append({
                "start": [x + radius * math.cos(a1), y + height, z + radius * math.sin(a1)],
                "end": [x + radius * math.cos(a2), y + height, z + radius * math.sin(a2)]
            })
        
        # Linee verticali (ogni 2 segmenti per non esagerare)
        for i in range(0, segments, 2):
            angle = (i / segments) * 2 * math.pi
            px = x + radius * math.cos(angle)
            pz = z + radius * math.sin(angle)
            lines.append({
                "start": [px, y, pz],
                "end": [px, y + height, pz]
            })
        
        return lines
    
    @staticmethod
    def sphere(x: float, y: float, z: float, radius: float, rings: int = 8, segments: int = 12) -> List[Dict]:
        """
        Genera una sfera wireframe
        x,y,z = centro
        """
        lines = []
        
        # Anelli orizzontali
        for i in range(1, rings):
            phi = (i / rings) * math.pi
            r = radius * math.sin(phi)
            cy = y + radius * math.cos(phi)
            
            for j in range(segments):
                a1 = (j / segments) * 2 * math.pi
                a2 = ((j + 1) / segments) * 2 * math.pi
                lines.append({
                    "start": [x + r * math.cos(a1), cy, z + r * math.sin(a1)],
                    "end": [x + r * math.cos(a2), cy, z + r * math.sin(a2)]
                })
        
        # Meridiani verticali
        for j in range(0, segments, 2):
            theta = (j / segments) * 2 * math.pi
            for i in range(rings):
                phi1 = (i / rings) * math.pi
                phi2 = ((i + 1) / rings) * math.pi
                lines.append({
                    "start": [
                        x + radius * math.sin(phi1) * math.cos(theta),
                        y + radius * math.cos(phi1),
                        z + radius * math.sin(phi1) * math.sin(theta)
                    ],
                    "end": [
                        x + radius * math.sin(phi2) * math.cos(theta),
                        y + radius * math.cos(phi2),
                        z + radius * math.sin(phi2) * math.sin(theta)
                    ]
                })
        
        return lines
    
    @staticmethod
    def cone(x: float, y: float, z: float, radius: float, height: float, segments: int = 16) -> List[Dict]:
        """Genera un cono wireframe"""
        lines = []
        
        # Cerchio base
        for i in range(segments):
            a1 = (i / segments) * 2 * math.pi
            a2 = ((i + 1) / segments) * 2 * math.pi
            lines.append({
                "start": [x + radius * math.cos(a1), y, z + radius * math.sin(a1)],
                "end": [x + radius * math.cos(a2), y, z + radius * math.sin(a2)]
            })
        
        # Linee al vertice
        apex = [x, y + height, z]
        for i in range(0, segments, 2):
            angle = (i / segments) * 2 * math.pi
            lines.append({
                "start": [x + radius * math.cos(angle), y, z + radius * math.sin(angle)],
                "end": apex
            })
        
        return lines
    
    @staticmethod
    def pyramid(x: float, y: float, z: float, base_w: float, base_d: float, height: float) -> List[Dict]:
        """Genera una piramide a base rettangolare"""
        hw, hd = base_w/2, base_d/2
        
        # Base
        base = [
            [x-hw, y, z-hd],
            [x+hw, y, z-hd],
            [x+hw, y, z+hd],
            [x-hw, y, z+hd],
        ]
        apex = [x, y + height, z]
        
        lines = [
            {"start": base[0], "end": base[1]},
            {"start": base[1], "end": base[2]},
            {"start": base[2], "end": base[3]},
            {"start": base[3], "end": base[0]},
            {"start": base[0], "end": apex},
            {"start": base[1], "end": apex},
            {"start": base[2], "end": apex},
            {"start": base[3], "end": apex},
        ]
        
        return lines
    
    @staticmethod
    def roof(x: float, y: float, z: float, w: float, d: float, height: float) -> List[Dict]:
        """Genera un tetto a due falde"""
        hw, hd = w/2, d/2
        
        # Base del tetto
        base = [
            [x-hw, y, z-hd],
            [x+hw, y, z-hd],
            [x+hw, y, z+hd],
            [x-hw, y, z+hd],
        ]
        # Cresta
        ridge = [
            [x, y + height, z-hd],
            [x, y + height, z+hd],
        ]
        
        lines = [
            # Base
            {"start": base[0], "end": base[1]},
            {"start": base[1], "end": base[2]},
            {"start": base[2], "end": base[3]},
            {"start": base[3], "end": base[0]},
            # Falde
            {"start": base[0], "end": ridge[0]},
            {"start": base[1], "end": ridge[0]},
            {"start": base[2], "end": ridge[1]},
            {"start": base[3], "end": ridge[1]},
            # Cresta
            {"start": ridge[0], "end": ridge[1]},
        ]
        
        return lines
    
    @staticmethod
    def window(x: float, y: float, z: float, w: float, h: float, facing: str = "z") -> List[Dict]:
        """
        Genera una finestra wireframe
        facing: "z" = frontale, "x" = laterale
        """
        hw, hh = w/2, h/2
        
        if facing == "z":
            # Cornice esterna
            frame = [
                [x-hw, y-hh, z], [x+hw, y-hh, z],
                [x+hw, y+hh, z], [x-hw, y+hh, z]
            ]
            # Croce interna
            cross = [
                ([x, y-hh, z], [x, y+hh, z]),
                ([x-hw, y, z], [x+hw, y, z]),
            ]
        else:  # facing == "x"
            frame = [
                [x, y-hh, z-hw], [x, y-hh, z+hw],
                [x, y+hh, z+hw], [x, y+hh, z-hw]
            ]
            cross = [
                ([x, y-hh, z], [x, y+hh, z]),
                ([x, y, z-hw], [x, y, z+hw]),
            ]
        
        lines = [
            {"start": frame[0], "end": frame[1]},
            {"start": frame[1], "end": frame[2]},
            {"start": frame[2], "end": frame[3]},
            {"start": frame[3], "end": frame[0]},
            {"start": cross[0][0], "end": cross[0][1]},
            {"start": cross[1][0], "end": cross[1][1]},
        ]
        
        return lines
    
    @staticmethod
    def door(x: float, y: float, z: float, w: float, h: float, facing: str = "z") -> List[Dict]:
        """Genera una porta wireframe"""
        hw = w/2
        
        if facing == "z":
            frame = [
                [x-hw, y, z], [x+hw, y, z],
                [x+hw, y+h, z], [x-hw, y+h, z]
            ]
            # Maniglia
            handle = [x+hw*0.7, y+h*0.5, z]
        else:
            frame = [
                [x, y, z-hw], [x, y, z+hw],
                [x, y+h, z+hw], [x, y+h, z-hw]
            ]
            handle = [x, y+h*0.5, z+hw*0.7]
        
        lines = [
            {"start": frame[0], "end": frame[1]},
            {"start": frame[1], "end": frame[2]},
            {"start": frame[2], "end": frame[3]},
            {"start": frame[3], "end": frame[0]},
        ]
        
        # Pannelli interni
        if facing == "z":
            lines.append({"start": [x-hw*0.8, y+h*0.1, z], "end": [x-hw*0.8, y+h*0.9, z]})
            lines.append({"start": [x+hw*0.3, y+h*0.1, z], "end": [x+hw*0.3, y+h*0.9, z]})
        
        return lines
    
    @staticmethod
    def stairs(x: float, y: float, z: float, w: float, total_h: float, total_d: float, steps: int) -> List[Dict]:
        """Genera una scala wireframe"""
        lines = []
        step_h = total_h / steps
        step_d = total_d / steps
        hw = w / 2
        
        for i in range(steps):
            sy = y + i * step_h
            sz = z + i * step_d
            
            # Piano del gradino
            lines.extend([
                {"start": [x-hw, sy+step_h, sz], "end": [x+hw, sy+step_h, sz]},
                {"start": [x-hw, sy+step_h, sz], "end": [x-hw, sy+step_h, sz+step_d]},
                {"start": [x+hw, sy+step_h, sz], "end": [x+hw, sy+step_h, sz+step_d]},
                {"start": [x-hw, sy+step_h, sz+step_d], "end": [x+hw, sy+step_h, sz+step_d]},
                # Alzata
                {"start": [x-hw, sy, sz], "end": [x-hw, sy+step_h, sz]},
                {"start": [x+hw, sy, sz], "end": [x+hw, sy+step_h, sz]},
            ])
        
        return lines
    
    @staticmethod
    def grid(x: float, y: float, z: float, w: float, d: float, divisions: int = 5) -> List[Dict]:
        """Genera una griglia/pavimento wireframe"""
        lines = []
        hw, hd = w/2, d/2
        
        # Linee parallele all'asse X
        for i in range(divisions + 1):
            t = i / divisions
            cz = z - hd + t * d
            lines.append({"start": [x-hw, y, cz], "end": [x+hw, y, cz]})
        
        # Linee parallele all'asse Z
        for i in range(divisions + 1):
            t = i / divisions
            cx = x - hw + t * w
            lines.append({"start": [cx, y, z-hd], "end": [cx, y, z+hd]})
        
        return lines
    
    @staticmethod
    def arc(x: float, y: float, z: float, radius: float, start_angle: float, end_angle: float, segments: int = 12, axis: str = "y") -> List[Dict]:
        """Genera un arco"""
        lines = []
        angle_range = end_angle - start_angle
        
        for i in range(segments):
            a1 = start_angle + (i / segments) * angle_range
            a2 = start_angle + ((i + 1) / segments) * angle_range
            
            if axis == "y":
                lines.append({
                    "start": [x + radius * math.cos(a1), y, z + radius * math.sin(a1)],
                    "end": [x + radius * math.cos(a2), y, z + radius * math.sin(a2)]
                })
            elif axis == "x":
                lines.append({
                    "start": [x, y + radius * math.cos(a1), z + radius * math.sin(a1)],
                    "end": [x, y + radius * math.cos(a2), z + radius * math.sin(a2)]
                })
            else:  # axis == "z"
                lines.append({
                    "start": [x + radius * math.cos(a1), y + radius * math.sin(a1), z],
                    "end": [x + radius * math.cos(a2), y + radius * math.sin(a2), z]
                })
        
        return lines
    
    @staticmethod
    def torus(x: float, y: float, z: float, major_r: float, minor_r: float, major_seg: int = 16, minor_seg: int = 8) -> List[Dict]:
        """Genera un toro (ciambella) wireframe"""
        lines = []
        
        # Anelli maggiori
        for i in range(major_seg):
            theta = (i / major_seg) * 2 * math.pi
            cx = x + major_r * math.cos(theta)
            cz = z + major_r * math.sin(theta)
            
            for j in range(minor_seg):
                phi1 = (j / minor_seg) * 2 * math.pi
                phi2 = ((j + 1) / minor_seg) * 2 * math.pi
                
                lines.append({
                    "start": [
                        cx + minor_r * math.cos(phi1) * math.cos(theta),
                        y + minor_r * math.sin(phi1),
                        cz + minor_r * math.cos(phi1) * math.sin(theta)
                    ],
                    "end": [
                        cx + minor_r * math.cos(phi2) * math.cos(theta),
                        y + minor_r * math.sin(phi2),
                        cz + minor_r * math.cos(phi2) * math.sin(theta)
                    ]
                })
        
        # Anelli minori (connessioni)
        for j in range(0, minor_seg, 2):
            phi = (j / minor_seg) * 2 * math.pi
            
            for i in range(major_seg):
                theta1 = (i / major_seg) * 2 * math.pi
                theta2 = ((i + 1) / major_seg) * 2 * math.pi
                
                cx1 = x + major_r * math.cos(theta1)
                cz1 = z + major_r * math.sin(theta1)
                cx2 = x + major_r * math.cos(theta2)
                cz2 = z + major_r * math.sin(theta2)
                
                lines.append({
                    "start": [
                        cx1 + minor_r * math.cos(phi) * math.cos(theta1),
                        y + minor_r * math.sin(phi),
                        cz1 + minor_r * math.cos(phi) * math.sin(theta1)
                    ],
                    "end": [
                        cx2 + minor_r * math.cos(phi) * math.cos(theta2),
                        y + minor_r * math.sin(phi),
                        cz2 + minor_r * math.cos(phi) * math.sin(theta2)
                    ]
                })
        
        return lines
    
    @staticmethod
    def capsule(x: float, y: float, z: float, radius: float, height: float, segments: int = 12) -> List[Dict]:
        """Genera una capsula (cilindro con semisfere alle estremità)"""
        lines = []
        
        # Cilindro centrale
        lines.extend(Component3D.cylinder(x, y + radius, z, radius, height - 2*radius, segments))
        
        # Semisfera superiore
        for i in range(1, segments//2):
            phi = (i / segments) * math.pi
            r = radius * math.sin(phi)
            cy = y + height - radius + radius * math.cos(phi)
            
            for j in range(segments):
                a1 = (j / segments) * 2 * math.pi
                a2 = ((j + 1) / segments) * 2 * math.pi
                lines.append({
                    "start": [x + r * math.cos(a1), cy, z + r * math.sin(a1)],
                    "end": [x + r * math.cos(a2), cy, z + r * math.sin(a2)]
                })
        
        # Semisfera inferiore
        for i in range(segments//2, segments):
            phi = (i / segments) * math.pi
            r = radius * math.sin(phi)
            cy = y + radius + radius * math.cos(phi)
            
            for j in range(segments):
                a1 = (j / segments) * 2 * math.pi
                a2 = ((j + 1) / segments) * 2 * math.pi
                lines.append({
                    "start": [x + r * math.cos(a1), cy, z + r * math.sin(a1)],
                    "end": [x + r * math.cos(a2), cy, z + r * math.sin(a2)]
                })
        
        return lines
    
    @staticmethod
    def hexagon(x: float, y: float, z: float, radius: float, height: float) -> List[Dict]:
        """Genera un prisma esagonale"""
        lines = []
        
        # Vertici esagono
        verts_bottom = []
        verts_top = []
        for i in range(6):
            angle = (i / 6) * 2 * math.pi + math.pi/6
            vx = x + radius * math.cos(angle)
            vz = z + radius * math.sin(angle)
            verts_bottom.append([vx, y, vz])
            verts_top.append([vx, y + height, vz])
        
        # Bordi esagono base e top
        for i in range(6):
            lines.append({"start": verts_bottom[i], "end": verts_bottom[(i+1)%6]})
            lines.append({"start": verts_top[i], "end": verts_top[(i+1)%6]})
            lines.append({"start": verts_bottom[i], "end": verts_top[i]})
        
        return lines


# ═══════════════════════════════════════════════════════════════════════════
# COMPONENT ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════

def assemble_components(components: List[Dict]) -> List[Dict]:
    """
    Assembla una lista di componenti in linee 3D
    Ogni componente: {"type": "cube", "x": 0, "y": 0, "z": 0, "params": {...}}
    """
    all_lines = []
    
    for comp in components:
        comp_type = comp.get("type", "").lower()
        x = comp.get("x", 0)
        y = comp.get("y", 0)
        z = comp.get("z", 0)
        params = comp.get("params", {})
        
        try:
            if comp_type == "cube" or comp_type == "box":
                lines = Component3D.cube(x, y, z, 
                    params.get("w", 1), params.get("h", 1), params.get("d", 1))
            
            elif comp_type == "cylinder":
                lines = Component3D.cylinder(x, y, z,
                    params.get("radius", 0.5), params.get("height", 1),
                    params.get("segments", 16))
            
            elif comp_type == "sphere":
                lines = Component3D.sphere(x, y, z,
                    params.get("radius", 0.5),
                    params.get("rings", 8), params.get("segments", 12))
            
            elif comp_type == "cone":
                lines = Component3D.cone(x, y, z,
                    params.get("radius", 0.5), params.get("height", 1),
                    params.get("segments", 16))
            
            elif comp_type == "pyramid":
                lines = Component3D.pyramid(x, y, z,
                    params.get("base_w", 1), params.get("base_d", 1),
                    params.get("height", 1))
            
            elif comp_type == "roof":
                lines = Component3D.roof(x, y, z,
                    params.get("w", 2), params.get("d", 2),
                    params.get("height", 1))
            
            elif comp_type == "window":
                lines = Component3D.window(x, y, z,
                    params.get("w", 0.8), params.get("h", 1),
                    params.get("facing", "z"))
            
            elif comp_type == "door":
                lines = Component3D.door(x, y, z,
                    params.get("w", 1), params.get("h", 2),
                    params.get("facing", "z"))
            
            elif comp_type == "stairs":
                lines = Component3D.stairs(x, y, z,
                    params.get("w", 1), params.get("total_h", 2),
                    params.get("total_d", 2), params.get("steps", 8))
            
            elif comp_type == "grid" or comp_type == "floor":
                lines = Component3D.grid(x, y, z,
                    params.get("w", 4), params.get("d", 4),
                    params.get("divisions", 5))
            
            elif comp_type == "torus":
                lines = Component3D.torus(x, y, z,
                    params.get("major_r", 1), params.get("minor_r", 0.3),
                    params.get("major_seg", 16), params.get("minor_seg", 8))
            
            elif comp_type == "capsule":
                lines = Component3D.capsule(x, y, z,
                    params.get("radius", 0.3), params.get("height", 1.5),
                    params.get("segments", 12))
            
            elif comp_type == "hexagon":
                lines = Component3D.hexagon(x, y, z,
                    params.get("radius", 0.5), params.get("height", 1))
            
            elif comp_type == "arc":
                lines = Component3D.arc(x, y, z,
                    params.get("radius", 1),
                    params.get("start_angle", 0),
                    params.get("end_angle", math.pi),
                    params.get("segments", 12),
                    params.get("axis", "y"))
            
            else:
                print(f"⚠️ Unknown component type: {comp_type}")
                continue
            
            all_lines.extend(lines)
            
        except Exception as e:
            print(f"❌ Error assembling {comp_type}: {e}")
    
    return all_lines


# ═══════════════════════════════════════════════════════════════════════════
# SCENE JSON VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════

def validate_and_repair_scene(scene_data: dict, prompt: str) -> dict:
    """Valida e ripara il Scene JSON prima di restituirlo al frontend"""
    valid_types = {
        "box", "sphere", "cylinder", "cone", "torus",
        "plane", "ring", "tetrahedron", "octahedron"
    }

    scene_data.setdefault("name", prompt.upper())
    scene_data.setdefault("code", "SCN-001")
    scene_data.setdefault("dimensions", {"width": "?", "height": "?", "depth": "?"})
    scene_data.setdefault("aiNotes", "")
    duration = float(scene_data.get("duration", 8.0))
    scene_data["duration"] = duration

    # Luci di default se mancanti
    if not scene_data.get("lights"):
        scene_data["lights"] = [
            {"type": "ambient", "color": "#001122", "intensity": 0.4},
            {"type": "point",   "color": "#00f0ff", "intensity": 3,   "position": [0, 6, 2],    "distance": 15},
            {"type": "point",   "color": "#00ff88", "intensity": 1.5, "position": [-3, 2, -2],  "distance": 10}
        ]

    # Valida e ripara ogni oggetto (cap 20)
    objects = scene_data.get("objects", [])
    if not objects:
        raise HTTPException(status_code=500, detail="No objects in scene")

    repaired = []
    for i, obj in enumerate(objects[:20]):
        # Geometry
        geo = obj.get("geometry", {})
        if geo.get("type", "").lower() not in valid_types:
            geo = {"type": "box", "args": [1, 1, 1]}
        if not geo.get("args"):
            geo["args"] = [1, 1, 1]
        geo["type"] = geo["type"].lower()
        obj["geometry"] = geo

        # Material
        mat = obj.get("material", {})
        mat.setdefault("type", "phong")
        mat.setdefault("color", "#00f0ff")
        mat.setdefault("emissive", "#003344")
        mat.setdefault("transparent", True)
        mat.setdefault("opacity", 0.25)
        obj["material"] = mat

        # Transform
        obj.setdefault("position", [0, 0, 0])
        obj.setdefault("rotation", [0, 0, 0])
        obj.setdefault("id", f"obj_{i}")
        obj.setdefault("label", f"Componente {i + 1}")

        # Animation
        anim = obj.get("animation", {})
        anim.setdefault("type", "fadeIn")
        anim.setdefault("delay", round((i / max(len(objects), 1)) * (duration * 0.8), 2))
        anim.setdefault("duration", 1.0)
        obj["animation"] = anim

        repaired.append(obj)

    scene_data["objects"] = repaired

    # Narration di default
    if not scene_data.get("narration"):
        name = scene_data["name"]
        scene_data["narration"] = [
            {"time": 0,               "text": f"Inizializzazione {name}..."},
            {"time": duration * 0.4,  "text": "Assemblaggio strutture..."},
            {"time": duration * 0.8,  "text": "Calibrazione materiali..."},
            {"time": duration,        "text": "Progetto completato."}
        ]

    return scene_data


# ═══════════════════════════════════════════════════════════════════════════
# SCENE TO WIREFRAME (compatibilità export STL/OBJ)
# ═══════════════════════════════════════════════════════════════════════════

def scene_to_wireframe_lines(scene_data: dict) -> List[Dict]:
    """Converte sceneData.objects nel formato linee per export STL/OBJ"""
    type_map = {
        "box": "cube",       "sphere": "sphere",     "cylinder": "cylinder",
        "cone": "cone",      "torus": "torus",        "plane": "cube",
        "ring": "torus",     "tetrahedron": "pyramid","octahedron": "pyramid"
    }
    args_map = {
        "box":       lambda a: {"w": a[0], "h": a[1], "d": a[2]},
        "sphere":    lambda a: {"radius": a[0]},
        "cylinder":  lambda a: {"radius": a[1], "height": a[2]},
        "cone":      lambda a: {"radius": a[0], "height": a[1]},
        "torus":     lambda a: {"major_r": a[0], "minor_r": a[1]},
        "plane":     lambda a: {"w": a[0], "h": 0.05, "d": a[1]},
        "ring":      lambda a: {"major_r": a[1], "minor_r": a[1] - a[0]},
        "tetrahedron": lambda a: {"base_w": a[0], "base_d": a[0], "height": a[0]},
        "octahedron":  lambda a: {"base_w": a[0], "base_d": a[0], "height": a[0]},
    }
    components = []
    for obj in scene_data.get("objects", []):
        geo  = obj.get("geometry", {})
        gtype = geo.get("type", "box")
        args  = geo.get("args", [1, 1, 1])
        pos   = obj.get("position", [0, 0, 0])
        mapper = args_map.get(gtype, lambda a: {"w": 1, "h": 1, "d": 1})
        components.append({
            "type": type_map.get(gtype, "cube"),
            "x": pos[0], "y": pos[1], "z": pos[2],
            "params": mapper(args)
        })
    return assemble_components(components)


# ═══════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════

class BlueprintRequest(BaseModel):
    prompt: str
    quality: str = "standard"

class ImageAnalysisRequest(BaseModel):
    image: str
    prompt: str = "Descrivi cosa vedi in questa immagine in italiano."

class ExportRequest(BaseModel):
    blueprint: dict
    format: str = "stl"

class ShareRequest(BaseModel):
    blueprint: dict
    title: str = "Progetto PINGIPOOL"

class ChatRequest(BaseModel):
    message: str
    context: str = ""

class RDAnalyzeRequest(BaseModel):
    problem: str
    query: str = ""

class RDSearchRequest(BaseModel):
    query: str


# ═══════════════════════════════════════════════════════════════════════════
# R&D MODE — PAPER & PATENT SEARCH + CLAUDE ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════

RD_SYSTEM_PROMPT = """Sei J.A.R.V.I.S., assistente R&D di livello avanzato del Signore. Ti vengono forniti paper scientifici e brevetti reali trovati nelle banche dati mondiali.

Analizza il problema posto dal Signore e:

1. STATO DELL'ARTE: riassumi le soluzioni esistenti trovate nei paper e brevetti (cita titoli e date reali)
2. GAP IDENTIFICATI: cosa NON è stato ancora risolto o brevettato
3. SOLUZIONI INNOVATIVE: proponi 3 soluzioni originali che combinano concetti da domini diversi. Per ogni soluzione:
   - Nome della soluzione
   - Principio di funzionamento
   - Materiali/tecnologie necessarie
   - Vantaggi rispetto allo stato dell'arte
   - Fattibilità (alta/media/bassa) con motivazione
   - Stima costi approssimativa
4. PROTOTIPO 3D: per la soluzione più promettente, genera una descrizione dettagliata di un oggetto fisico che possa essere modellato in 3D (forma, dimensioni, componenti visibili)

Rispondi in italiano. Sii concreto, basati sui dati reali forniti, non inventare riferimenti."""


def _rebuild_abstract(inverted_index):
    """Ricostruisce testo da OpenAlex abstract_inverted_index {"word": [pos1, pos2, ...]}"""
    if not inverted_index:
        return ""
    words = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words.keys()))


async def _search_papers_openalex(query: str) -> list:
    """Cerca paper scientifici su OpenAlex (gratuito, no API key)"""
    import urllib.parse
    encoded = urllib.parse.quote(query)
    url = f"https://api.openalex.org/works?search={encoded}&per_page=10&sort=relevance_score:desc&mailto=pingipool@example.com"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=15.0)
            if resp.status_code != 200:
                print(f"[RD] OpenAlex error {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()
            papers = []
            for work in data.get("results", []):
                papers.append({
                    "title": work.get("title", ""),
                    "abstract": _rebuild_abstract(work.get("abstract_inverted_index")),
                    "publication_date": work.get("publication_date", ""),
                    "doi": work.get("doi", ""),
                    "cited_by_count": work.get("cited_by_count", 0),
                    "source": ((work.get("primary_location") or {}).get("source") or {}).get("display_name", "")
                })
            print(f"[RD] OpenAlex: {len(papers)} paper trovati per '{query[:50]}'")
            return papers
    except Exception as e:
        print(f"[RD] OpenAlex exception: {e}")
        return []


async def _search_patents_patentsview(query: str) -> list:
    """Cerca brevetti — usa Google Patents via SerpAPI-free (Crossref fallback)"""
    import urllib.parse
    # Strategia: cerca su OpenAlex con filtro type = patent-related
    # OpenAlex non ha brevetti diretti, usiamo Crossref che include alcuni brevetti/standards
    encoded = urllib.parse.quote(query + " patent")
    url = f"https://api.openalex.org/works?search={encoded}&per_page=10&filter=type:standard|type:report&mailto=pingipool@example.com"
    try:
        async with httpx.AsyncClient() as client:
            # Prova OpenAlex con filtro standard/report (include technical standards e patent refs)
            resp = await client.get(url, timeout=15.0)
            patents = []
            if resp.status_code == 200:
                data = resp.json()
                for work in data.get("results", []):
                    doi = work.get("doi", "")
                    patents.append({
                        "number": doi.split("/")[-1] if doi else work.get("id", "").split("/")[-1],
                        "title": work.get("title", ""),
                        "abstract": _rebuild_abstract(work.get("abstract_inverted_index"))[:500],
                        "date": work.get("publication_date", ""),
                        "assignee": ((work.get("primary_location") or {}).get("source") or {}).get("display_name", "")
                    })

            # Fallback: cerca su Crossref per patent-related
            if len(patents) < 3:
                cross_url = f"https://api.crossref.org/works?query={urllib.parse.quote(query)}&filter=type:standard&rows=10&mailto=pingipool@example.com"
                resp2 = await client.get(cross_url, timeout=10.0)
                if resp2.status_code == 200:
                    items = resp2.json().get("message", {}).get("items", [])
                    for item in items:
                        patents.append({
                            "number": item.get("DOI", ""),
                            "title": item.get("title", [""])[0] if item.get("title") else "",
                            "abstract": "",
                            "date": "-".join(str(x) for x in item.get("created", {}).get("date-parts", [[]])[0]) if item.get("created") else "",
                            "assignee": item.get("publisher", "")
                        })

            print(f"[RD] Patents/Standards: {len(patents)} trovati per '{query[:50]}'")
            return patents
    except Exception as e:
        print(f"[RD] Patents search exception: {e}")
        return []


@app.post("/api/rd/search-papers")
async def rd_search_papers(request: RDSearchRequest):
    papers = await _search_papers_openalex(request.query)
    return {"papers": papers}


@app.post("/api/rd/search-patents")
async def rd_search_patents(request: RDSearchRequest):
    patents = await _search_patents_patentsview(request.query)
    return {"patents": patents}


@app.post("/api/rd/analyze")
async def rd_analyze(request: RDAnalyzeRequest):
    """R&D completo: paper + brevetti + analisi Claude"""
    import asyncio
    search_query = request.query or request.problem

    # Ricerca parallela paper + brevetti
    papers, patents = await asyncio.gather(
        _search_papers_openalex(search_query),
        _search_patents_patentsview(search_query)
    )

    # Componi contesto per Claude
    context_parts = [f"PROBLEMA DEL SIGNORE:\n{request.problem}\n"]

    if papers:
        context_parts.append("PAPER SCIENTIFICI TROVATI:")
        for i, p in enumerate(papers[:8], 1):
            abstract_preview = (p["abstract"] or "N/A")[:300]
            context_parts.append(f"{i}. \"{p['title']}\" ({p['publication_date']}) — Citazioni: {p['cited_by_count']}\n   Abstract: {abstract_preview}")

    if patents:
        context_parts.append("\nBREVETTI TROVATI:")
        for i, pt in enumerate(patents[:8], 1):
            context_parts.append(f"{i}. US{pt['number']} — \"{pt['title']}\" ({pt['date']}) — {pt['assignee']}\n   Abstract: {pt['abstract'][:300]}")

    if not papers and not patents:
        context_parts.append("\nNessun paper o brevetto trovato nelle banche dati. Basa l'analisi sulla tua conoscenza.")

    user_message = "\n".join(context_parts)

    # Chiama Claude
    analysis_text = ""
    prototype_prompt = ""
    if ANTHROPIC_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    ANTHROPIC_URL,
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 4096,
                        "system": RD_SYSTEM_PROMPT,
                        "messages": [{"role": "user", "content": user_message}]
                    },
                    timeout=60.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    analysis_text = data["content"][0]["text"]
                    # Estrai sezione PROTOTIPO 3D
                    proto_markers = ["PROTOTIPO 3D", "Prototipo 3D", "prototipo 3d", "PROTOTIPO"]
                    for marker in proto_markers:
                        if marker in analysis_text:
                            idx = analysis_text.index(marker)
                            prototype_prompt = analysis_text[idx:].split("\n\n", 2)[-1][:500]
                            break
                    if not prototype_prompt:
                        prototype_prompt = f"Prototipo di {request.problem}"
                    print(f"[RD] Claude analysis OK ({len(analysis_text)} chars)")
                else:
                    print(f"[RD] Claude error {resp.status_code}: {resp.text[:200]}")
                    analysis_text = "Errore nell'analisi AI. I dati di ricerca sono comunque disponibili."
        except Exception as e:
            print(f"[RD] Claude exception: {e}")
            analysis_text = f"Errore nell'analisi AI: {str(e)}"
    else:
        analysis_text = "ANTHROPIC_API_KEY non configurata. Impossibile eseguire l'analisi AI."

    return {
        "success": True,
        "analysis": analysis_text,
        "papers": papers,
        "patents": patents,
        "prototype_prompt": prototype_prompt
    }


# Compat endpoints for existing frontend
@app.post("/api/research")
async def api_research(request: RDSearchRequest):
    papers = await _search_papers_openalex(request.query)
    return {"results": [{"title": p["title"], "snippet": p["abstract"][:200]} for p in papers]}


@app.post("/api/generate-solutions")
async def api_generate_solutions(request: Request):
    body = await request.json()
    problem = body.get("request", body.get("problem", ""))
    rd_req = RDAnalyzeRequest(problem=problem)
    result = await rd_analyze(rd_req)
    # Map to legacy solution card format
    solutions = []
    analysis = result.get("analysis", "")
    # Parse 3 solutions from Claude's text
    sol_names = []
    for line in analysis.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- Nome") or stripped.startswith("- **Nome"):
            name = stripped.split(":", 1)[-1].strip().strip("*").strip()
            sol_names.append(name)
    # Build at least 3 solution cards
    for i in range(3):
        solutions.append({
            "id": i + 1,
            "name": sol_names[i] if i < len(sol_names) else f"Soluzione {chr(65+i)}",
            "description": analysis[i*500:(i+1)*500] if analysis else f"Soluzione {chr(65+i)} basata sull'analisi R&D",
            "pros": ["Basata su ricerca scientifica", "Approccio innovativo"],
            "cons": ["Richiede validazione sperimentale"],
            "difficulty": 3,
            "cost": ["basso", "medio", "alto"][i],
            "time": f"{(i+1)*3} mesi",
            "specs": {"materials": [], "dimensions": "Da definire", "power": "Da definire"}
        })
    return {"solutions": solutions, "analysis": analysis, "papers": result.get("papers", []), "patents": result.get("patents", [])}


@app.post("/api/modify-solution")
async def api_modify_solution(request: Request):
    body = await request.json()
    original = body.get("solution", {})
    modification = body.get("modification", "")
    return {"solution": {**original, "name": original.get("name", "") + " (modificata)", "description": modification}}


@app.post("/api/generate-alternative")
async def api_generate_alternative(request: Request):
    body = await request.json()
    base = body.get("solution", {})
    return {"solution": {**base, "id": base.get("id", 0) + 10, "name": base.get("name", "") + " — Alternativa"}}


# ═══════════════════════════════════════════════════════════════════════════
# AI PROMPT - LEGACY (mantenuto per compatibilità export STL/OBJ)
# ═══════════════════════════════════════════════════════════════════════════

COMPONENT_PROMPT_LEGACY = """Sei J.A.R.V.I.S., il sistema di progettazione 3D di Stark Industries.

INVECE di generare coordinate 3D manualmente, devi ASSEMBLARE COMPONENTI PRE-DEFINITI.

COMPONENTI: cube, cylinder, sphere, cone, pyramid, roof, window, door, stairs, grid, torus, capsule, hexagon
RISPONDI SOLO CON JSON VALIDO.
"""


# ═══════════════════════════════════════════════════════════════════════════
# AI PROMPT - SCENE JSON (sistema attivo)
# ═══════════════════════════════════════════════════════════════════════════

SCENE_PROMPT = """Sei J.A.R.V.I.S., il sistema di progettazione 3D olografica di PINGIPOOL.
Genera una scena 3D in formato JSON strutturato interpretato da Three.js nel browser.

═══════════════════════════════════════════════════════════════════════════
GEOMETRIE DISPONIBILI
═══════════════════════════════════════════════════════════════════════════

{"type":"box",         "args":[width, height, depth]}
{"type":"sphere",      "args":[radius, 16, 12]}
{"type":"cylinder",    "args":[radiusTop, radiusBottom, height, 16]}
{"type":"cone",        "args":[radius, height, 8]}
{"type":"torus",       "args":[radius, tube, 16, 32]}
{"type":"plane",       "args":[width, height]}
{"type":"ring",        "args":[innerRadius, outerRadius, 32]}
{"type":"tetrahedron", "args":[radius, 0]}
{"type":"octahedron",  "args":[radius, 0]}

═══════════════════════════════════════════════════════════════════════════
MATERIALI
═══════════════════════════════════════════════════════════════════════════

{
  "type":        "phong",    // "phong" | "standard" | "basic"
  "color":       "#00f0ff",  // colore principale
  "emissive":    "#003344",  // glow interno (~1/4 del colore principale)
  "transparent": true,
  "opacity":     0.25,       // 0.15-0.5 per stile olografico
  "wireframe":   false,      // true per strutture scheletriche
  "side":        "double"    // "front" | "back" | "double"
}

═══════════════════════════════════════════════════════════════════════════
PALETTE COLORI PINGIPOOL
═══════════════════════════════════════════════════════════════════════════

Strutture principali : color "#00f0ff", emissive "#003344"
Accenti e dettagli   : color "#00ff88", emissive "#002211"
Energia e pericolo   : color "#ff6600", emissive "#331100"
Basi e fondamenta    : color "#004466", emissive "#001122"
USA SEMPRE transparent:true con opacity 0.15-0.5 per effetto olografico.

═══════════════════════════════════════════════════════════════════════════
ANIMAZIONI PER OGGETTO
═══════════════════════════════════════════════════════════════════════════

Ogni oggetto ha: "animation": {"type": ..., "delay": secondi, "duration": secondi}

"fadeIn"  : appare per opacita    — {"type":"fadeIn",  "delay":0,   "duration":1.0}
"buildUp" : cresce dal basso      — {"type":"buildUp", "delay":0.5, "duration":1.5}
"assemble": esplode dal centro    — {"type":"assemble","delay":1.0, "duration":1.2}
"slideIn" : entra da offset       — {"type":"slideIn", "delay":0,   "duration":1.0, "from":[0,-3,0]}
"rotate"  : rotazione continua    — {"type":"rotate",  "delay":0,   "duration":0,   "axis":"y", "speed":0.01}
"pulse"   : pulsazione continua   — {"type":"pulse",   "delay":0,   "duration":0,   "minScale":0.95, "maxScale":1.05}

Usa delay progressivo: oggetto 0 a delay 0s, ultimo a delay (duration-2)s.

═══════════════════════════════════════════════════════════════════════════
LUCI (array "lights", 2-4 elementi)
═══════════════════════════════════════════════════════════════════════════

{"type":"ambient",     "color":"#001122", "intensity":0.4}
{"type":"point",       "color":"#00f0ff", "intensity":3,   "position":[0,6,2],   "distance":15}
{"type":"point",       "color":"#00ff88", "intensity":1.5, "position":[-3,2,-2], "distance":10}
{"type":"directional", "color":"#ffffff", "intensity":0.3, "position":[5,10,5]}

═══════════════════════════════════════════════════════════════════════════
STRUTTURA JSON DA GENERARE
═══════════════════════════════════════════════════════════════════════════

{
  "name": "NOME PROGETTO MAIUSCOLO",
  "code": "SCN-XXX",
  "dimensions": {"width":"Xm","height":"Ym","depth":"Zm"},
  "objects": [
    {
      "id":       "base",
      "label":    "Fondamenta",
      "geometry": {"type":"box","args":[4,0.2,3]},
      "material": {"type":"phong","color":"#004466","emissive":"#001122",
                   "transparent":true,"opacity":0.6,"side":"double"},
      "position": [0,0,0],
      "rotation": [0,0,0],
      "animation":{"type":"fadeIn","delay":0,"duration":0.8}
    },
    {
      "id":       "walls",
      "label":    "Struttura portante",
      "geometry": {"type":"box","args":[4,2.5,3]},
      "material": {"type":"phong","color":"#00f0ff","emissive":"#003344",
                   "transparent":true,"opacity":0.25,"side":"double"},
      "position": [0,1.25,0],
      "rotation": [0,0,0],
      "animation":{"type":"buildUp","delay":0.8,"duration":2.0}
    }
  ],
  "lights": [
    {"type":"ambient","color":"#001122","intensity":0.4},
    {"type":"point","color":"#00f0ff","intensity":3,"position":[0,6,2],"distance":15},
    {"type":"point","color":"#00ff88","intensity":1.5,"position":[-3,2,-2],"distance":10}
  ],
  "metadata": {
    "parts":    [{"name":"Struttura","qty":"1"}],
    "materials":[{"name":"Vetro olografico","qty":"20 m2"}]
  },
  "aiNotes": "Breve descrizione del progetto",
  "duration": 8
}

═══════════════════════════════════════════════════════════════════════════
REGOLE
═══════════════════════════════════════════════════════════════════════════

1. Massimo 20 oggetti per scena
2. Ogni oggetto DEVE avere: id, geometry (con args), material, position, animation
3. La scena deve essere chiaramente riconoscibile come l'oggetto richiesto
4. Usa la palette PINGIPOOL (cyan/verde su sfondo scuro)
5. RISPONDI SOLO CON JSON VALIDO — NIENTE TESTO, NIENTE MARKDOWN

═══════════════════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "PINGIPOOL J.A.R.V.I.S. v5 HYBRID",
        "model": GEMINI_MODEL,
        "system": "Component-Based 3D Assembly",
        "components": ["cube", "cylinder", "sphere", "cone", "pyramid", "roof", 
                      "window", "door", "stairs", "grid", "torus", "capsule", "hexagon"],
        "features": ["hybrid-3d", "voice", "vision", "export", "share"]
    }


@app.get("/components")
async def list_components():
    """Lista tutti i componenti disponibili"""
    return {
        "cube": {"desc": "Parallelepipedo", "params": ["w", "h", "d"]},
        "cylinder": {"desc": "Cilindro verticale", "params": ["radius", "height", "segments"]},
        "sphere": {"desc": "Sfera", "params": ["radius", "rings", "segments"]},
        "cone": {"desc": "Cono", "params": ["radius", "height", "segments"]},
        "pyramid": {"desc": "Piramide", "params": ["base_w", "base_d", "height"]},
        "roof": {"desc": "Tetto a falde", "params": ["w", "d", "height"]},
        "window": {"desc": "Finestra", "params": ["w", "h", "facing"]},
        "door": {"desc": "Porta", "params": ["w", "h", "facing"]},
        "stairs": {"desc": "Scala", "params": ["w", "total_h", "total_d", "steps"]},
        "grid": {"desc": "Griglia/Pavimento", "params": ["w", "d", "divisions"]},
        "torus": {"desc": "Ciambella", "params": ["major_r", "minor_r"]},
        "capsule": {"desc": "Capsula", "params": ["radius", "height"]},
        "hexagon": {"desc": "Prisma esagonale", "params": ["radius", "height"]},
    }


@app.post("/api/ephemeral-key")
async def get_ephemeral_key():
    """OpenAI Realtime - VOCE"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-realtime-preview-2024-12-17",
                "voice": "echo",
                "instructions": """Sei J.A.R.V.I.S., l'assistente AI di PINGIPOOL.

REGOLA ASSOLUTA: Parla SEMPRE e SOLO in italiano. MAI in inglese.

PERSONALITÀ:
- Chiama l'utente "Signore"
- Risposte brevi (max 2-3 frasi)
- Professionale con ironia

Quando l'utente chiede di costruire qualcosa, usa la funzione show_3d_build.
Il sistema usa componenti 3D pre-definiti per costruzioni precise."""
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="OpenAI error")
        
        data = response.json()
        return {"key": data.get("client_secret", {}).get("value", "")}


@app.post("/generate-blueprint")
async def generate_blueprint(request: BlueprintRequest):
    """Genera scena 3D olografica con Scene JSON"""

    print(f"\n🎨 Scene JSON: '{request.prompt}'")

    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    full_prompt = f"""{SCENE_PROMPT}
═══════════════════════════════════════════════════════════════════════════
RICHIESTA UTENTE: {request.prompt}
═══════════════════════════════════════════════════════════════════════════

Crea una scena 3D olografica che rappresenti "{request.prompt}".
Geometrie reali con materiali trasparenti stile PINGIPOOL.
Animazioni progressive che costruiscono l'oggetto pezzo per pezzo.

GENERA SOLO IL JSON (niente testo, niente markdown):"""

    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "maxOutputTokens": 8192,
                        "topP": 0.9
                    }
                },
                timeout=60.0
            )

            print(f"📥 Gemini Status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ Gemini error: {response.text}")
                raise HTTPException(status_code=response.status_code, detail="Gemini error")

            data = response.json()

            if "candidates" not in data or len(data["candidates"]) == 0:
                raise HTTPException(status_code=500, detail="Empty response")

            candidate = data["candidates"][0]

            if "content" not in candidate:
                reason = candidate.get("finishReason", "unknown")
                raise HTTPException(status_code=500, detail=f"Blocked: {reason}")

            response_text = candidate["content"]["parts"][0]["text"].strip()
            print(f"📝 AI Response: {len(response_text)} chars")

            # Pulisci markdown
            if response_text.startswith("```"):
                response_text = re.sub(r'^```json?\n?', '', response_text)
                response_text = re.sub(r'\n?```$', '', response_text)
                response_text = response_text.strip()

            # Parse JSON
            try:
                ai_design = json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"❌ JSON error: {e}")
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    ai_design = json.loads(json_match.group())
                else:
                    raise HTTPException(status_code=500, detail="Invalid JSON from AI")

            # Valida e ripara il Scene JSON
            scene_data = validate_and_repair_scene(ai_design, request.prompt)
            obj_count = len(scene_data["objects"])
            print(f"✅ Scene JSON: {scene_data['name']} | {obj_count} oggetti | {scene_data['duration']}s")

            return {
                "success":     True,
                "sceneData":   scene_data,
                "objectCount": obj_count,
                "system":      "scene-json",
                "engine":      GEMINI_MODEL
            }

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_fallback(request: ChatRequest):
    """Chat testuale fallback"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": """Sei J.A.R.V.I.S., l'assistente AI di PINGIPOOL.
Parla SEMPRE in italiano. Chiama l'utente "Signore".
Risposte BREVI. Professionale con ironia."""
                        },
                        {"role": "user", "content": request.message}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="OpenAI error")
            
            data = response.json()
            return {
                "response": data["choices"][0]["message"]["content"],
                "model": "gpt-4o-mini",
                "success": True
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT (riutilizzato dal v4)
# ═══════════════════════════════════════════════════════════════════════════

def lines_to_stl(blueprint: dict) -> bytes:
    """Converte linee in STL"""
    lines = blueprint.get("lines", [])
    triangles = []
    tube_radius = 0.015
    segments = 6
    
    for line_data in lines:
        start = line_data.get("start", [0,0,0])
        end = line_data.get("end", [0,0,0])
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        length = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        if length < 0.001:
            continue
        
        if abs(dy) < 0.99:
            perp1 = [-dz, 0, dx]
        else:
            perp1 = [1, 0, 0]
        
        p1_len = math.sqrt(perp1[0]**2 + perp1[1]**2 + perp1[2]**2)
        if p1_len > 0:
            perp1 = [p/p1_len * tube_radius for p in perp1]
        
        perp2 = [
            dy * perp1[2] - dz * perp1[1],
            dz * perp1[0] - dx * perp1[2],
            dx * perp1[1] - dy * perp1[0]
        ]
        p2_len = math.sqrt(perp2[0]**2 + perp2[1]**2 + perp2[2]**2)
        if p2_len > 0.001:
            perp2 = [p/p2_len * tube_radius for p in perp2]
        
        for i in range(segments):
            angle1 = (i / segments) * 2 * math.pi
            angle2 = ((i + 1) / segments) * 2 * math.pi
            
            c1, s1 = math.cos(angle1), math.sin(angle1)
            c2, s2 = math.cos(angle2), math.sin(angle2)
            
            p1_start = [start[j] + perp1[j]*c1 + perp2[j]*s1 for j in range(3)]
            p2_start = [start[j] + perp1[j]*c2 + perp2[j]*s2 for j in range(3)]
            p1_end = [end[j] + perp1[j]*c1 + perp2[j]*s1 for j in range(3)]
            p2_end = [end[j] + perp1[j]*c2 + perp2[j]*s2 for j in range(3)]
            
            triangles.append((p1_start, p2_start, p1_end))
            triangles.append((p2_start, p2_end, p1_end))
    
    stl_lines = ["solid blueprint"]
    for tri in triangles:
        v1 = [tri[1][i] - tri[0][i] for i in range(3)]
        v2 = [tri[2][i] - tri[0][i] for i in range(3)]
        normal = [
            v1[1]*v2[2] - v1[2]*v2[1],
            v1[2]*v2[0] - v1[0]*v2[2],
            v1[0]*v2[1] - v1[1]*v2[0]
        ]
        n_len = math.sqrt(sum(n**2 for n in normal))
        normal = [n/n_len for n in normal] if n_len > 0 else [0, 0, 1]
        
        stl_lines.append(f"  facet normal {normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}")
        stl_lines.append("    outer loop")
        for vertex in tri:
            stl_lines.append(f"      vertex {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}")
        stl_lines.append("    endloop")
        stl_lines.append("  endfacet")
    stl_lines.append("endsolid blueprint")
    
    return "\n".join(stl_lines).encode('utf-8')


@app.post("/api/export-stl")
async def export_stl(request: ExportRequest):
    try:
        bp = request.blueprint
        # Supporta sia vecchio formato (lines) che nuovo (objects)
        if "objects" in bp and "lines" not in bp:
            lines = scene_to_wireframe_lines(bp)
            bp = {"lines": lines, "name": bp.get("name", "project")}
        stl_content = lines_to_stl(bp)
        filename = bp.get('name', 'project').replace(' ', '_')
        return Response(
            content=stl_content,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}.stl"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# ANALYZE IMAGE (Claude Vision)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/analyze-image")
async def analyze_image(request: ImageAnalysisRequest):
    """Analisi immagine con Claude Vision (claude-sonnet-4-6)"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=500, detail="Anthropic API key not configured")

    try:
        image_data = request.image
        media_type = "image/jpeg"
        if "," in image_data:
            header, image_data = image_data.split(",", 1)
            if "png" in header:
                media_type = "image/png"
            elif "webp" in header:
                media_type = "image/webp"

        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "messages": [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {"type": "text", "text": request.prompt}
                        ]
                    }]
                },
                timeout=30.0
            )
            if response.status_code != 200:
                err_body = response.text
                print(f"[ERR] Anthropic Vision {response.status_code}: {err_body}")
                raise HTTPException(status_code=response.status_code, detail=f"Anthropic error: {err_body[:200]}")
            data = response.json()
            return {
                "success": True,
                "analysis": data["content"][0]["text"],
                "model": "claude-sonnet-4-20250514"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT OBJ
# ═══════════════════════════════════════════════════════════════════════════

def lines_to_obj(blueprint: dict) -> str:
    """Converte linee in formato OBJ wireframe"""
    lines_data = blueprint.get("lines", [])
    name = blueprint.get("name", "project")
    vertices = []
    edges = []
    vertex_map = {}

    def add_vertex(v):
        key = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
        if key not in vertex_map:
            vertex_map[key] = len(vertices) + 1
            vertices.append(key)
        return vertex_map[key]

    for line_data in lines_data:
        start = line_data.get("start", [0, 0, 0])
        end = line_data.get("end", [0, 0, 0])
        v1 = add_vertex(start)
        v2 = add_vertex(end)
        if v1 != v2:
            edges.append((v1, v2))

    obj_lines = [
        f"# PINGIPOOL Blueprint - {name}",
        f"# Generated: {datetime.now().isoformat()}",
        f"o {name.replace(' ', '_')}",
        ""
    ]
    for v in vertices:
        obj_lines.append(f"v {v[0]:.4f} {v[1]:.4f} {v[2]:.4f}")
    obj_lines.append("")
    for e in edges:
        obj_lines.append(f"l {e[0]} {e[1]}")
    return "\n".join(obj_lines)


@app.post("/api/export-obj")
async def export_obj(request: ExportRequest):
    try:
        bp = request.blueprint
        # Supporta sia vecchio formato (lines) che nuovo (objects)
        if "objects" in bp and "lines" not in bp:
            lines = scene_to_wireframe_lines(bp)
            bp = {"lines": lines, "name": bp.get("name", "project")}
        obj_content = lines_to_obj(bp)
        filename = bp.get('name', 'project').replace(' ', '_')
        return Response(
            content=obj_content.encode('utf-8'),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={filename}.obj"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT PDF (HTML specs)
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/export-pdf")
async def export_pdf(request: ExportRequest):
    """Genera HTML specs del blueprint scaricabile"""
    try:
        bp = request.blueprint
        name = bp.get("name", "Progetto")
        code = bp.get("code", "PRJ-001")
        dims = bp.get("dimensions", {})
        components = bp.get("components", [])
        materials = bp.get("materials", [])
        ai_notes = bp.get("aiNotes", "")
        line_count = len(bp.get("lines", []))

        comp_rows = "".join(
            f"<tr><td>{c.get('name','')}</td><td>{c.get('qty','')}</td></tr>"
            for c in components
        )
        mat_rows = "".join(
            f"<tr><td>{m.get('name','')}</td><td>{m.get('qty','')}</td></tr>"
            for m in materials
        )
        notes_block = f"<h2>Note AI</h2><div class='notes'>{ai_notes}</div>" if ai_notes else ""

        html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>PINGIPOOL - {name}</title>
<style>
  body {{ font-family: 'Courier New', monospace; background: #000408; color: #00f0ff; margin: 40px; }}
  h1 {{ color: #00ff88; border-bottom: 1px solid #00f0ff; padding-bottom: 10px; }}
  h2 {{ color: #00f0ff; margin-top: 30px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
  th {{ background: #001a1a; color: #00ff88; padding: 8px; text-align: left; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #002a2a; }}
  .meta {{ color: #888; font-size: 12px; }}
  .notes {{ background: #001a1a; padding: 15px; border-left: 3px solid #00f0ff; margin: 10px 0; }}
</style>
</head>
<body>
<h1>◈ {name}</h1>
<p class="meta">Codice: {code} | Wireframe: {line_count} linee | {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
<h2>Dimensioni</h2>
<table>
  <tr><th>Asse</th><th>Valore</th></tr>
  <tr><td>Larghezza</td><td>{dims.get('width','?')}</td></tr>
  <tr><td>Altezza</td><td>{dims.get('height','?')}</td></tr>
  <tr><td>Profondità</td><td>{dims.get('depth','?')}</td></tr>
</table>
<h2>Componenti</h2>
<table><tr><th>Nome</th><th>Quantità</th></tr>{comp_rows or "<tr><td colspan='2'>—</td></tr>"}</table>
<h2>Materiali</h2>
<table><tr><th>Nome</th><th>Quantità</th></tr>{mat_rows or "<tr><td colspan='2'>—</td></tr>"}</table>
{notes_block}
<p class="meta">PINGIPOOL J.A.R.V.I.S. v5 HYBRID</p>
</body>
</html>"""

        filename = name.replace(' ', '_')
        return HTMLResponse(
            content=html,
            headers={"Content-Disposition": f"attachment; filename={filename}_specs.html"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# SHARE PROJECT
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/share")
async def share_project(request: ShareRequest):
    """Salva blueprint in memoria e restituisce share URL"""
    try:
        share_id = str(uuid.uuid4())[:8].upper()
        shared_projects[share_id] = {
            "id": share_id,
            "title": request.title,
            "blueprint": request.blueprint,
            "created": datetime.now().isoformat()
        }
        if len(shared_projects) > 50:
            oldest_key = next(iter(shared_projects))
            del shared_projects[oldest_key]
        return {
            "success": True,
            "shareId": share_id,
            "shareUrl": f"https://pingipool-backend-75ej.onrender.com/share/{share_id}",
            "title": request.title
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/share/{share_id}")
async def get_shared_project(share_id: str):
    """Recupera progetto condiviso tramite ID"""
    project = shared_projects.get(share_id.upper())
    if not project:
        raise HTTPException(status_code=404, detail="Progetto non trovato")
    return project


@app.post("/api/generate-3d")
async def generate_3d_model(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt required")

        print(f"\n🎨 generate-3d: '{prompt}'")

        # Ottimizza il prompt in inglese per Rodin
        optimized_prompt = prompt
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                opt_resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                    json={"contents": [{"parts": [{"text": f"Translate to English and make it a detailed 3D model description for AI generation (max 50 words, focus on the object itself): {prompt}"}]}]}
                )
                opt_json = opt_resp.json()
                optimized_prompt = opt_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                print(f"Prompt ottimizzato: {optimized_prompt}")
        except Exception as e:
            print(f"Prompt optimization error: {e}")

        # Step 1: Submit job to fal.ai Rodin
        async with httpx.AsyncClient(timeout=60) as client:
            submit_resp = await client.post(
                "https://queue.fal.run/fal-ai/hyper3d/rodin",
                headers={
                    "Authorization": f"Key {FAL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": optimized_prompt,
                    "geometry_file_format": "glb",
                    "material": "PBR",
                    "quality": "medium"
                }
            )
            print(f"📡 fal.ai submit status: {submit_resp.status_code}")
            print(f"📡 fal.ai submit body: {submit_resp.text[:500]}")
            submit_data = submit_resp.json()
            request_id = submit_data.get("request_id")
            if not request_id:
                raise Exception(f"No request_id from fal.ai: {submit_data}")
            # Usa gli URL restituiti direttamente da fal.ai
            status_url = submit_data.get("status_url")
            result_url = submit_data.get("response_url")
            print(f"✅ request_id: {request_id}")
            print(f"📊 status_url: {status_url}")

        # Step 2: Poll status (max 240 secondi)

        async with httpx.AsyncClient(timeout=30) as client:
            for attempt in range(80):  # 80 * 3s = 240s max
                await asyncio.sleep(3 if attempt < 20 else 5)
                status_resp = await client.get(
                    status_url,
                    headers={"Authorization": f"Key {FAL_API_KEY}"}
                )
                status_data = status_resp.json()
                status = status_data.get("status", "")

                if status == "COMPLETED":
                    # Fetch result
                    result_resp = await client.get(
                        result_url,
                        headers={"Authorization": f"Key {FAL_API_KEY}"}
                    )
                    result_data = result_resp.json()

                    # Estrai URL del GLB
                    model_url = None
                    outputs = result_data.get("model_mesh", {})
                    if isinstance(outputs, dict):
                        model_url = outputs.get("url")
                    if not model_url:
                        # fallback: cerca nel dict
                        for key, val in result_data.items():
                            if isinstance(val, dict) and "url" in val:
                                model_url = val["url"]
                                break

                    # Genera componenti intelligenti con Gemini
                    components_prompt = f"""Analizza questo oggetto 3D: "{prompt}"
Genera una lista di 6-8 componenti tecnici principali con le loro posizioni approssimative
in coordinate 3D normalizzate (x,y,z tra -1 e 1, y=0 è il centro, y=1 è la cima).
Rispondi SOLO con JSON valido in questo formato:
{{
  "components": [
    {{"name": "HELMET VISOR", "position": [0, 0.9, 0.3], "description": "Protective transparent shield"}},
    {{"name": "CHEST ARMOR", "position": [0, 0.3, 0.2], "description": "Titanium alloy plating"}}
  ]
}}"""

                    components_data = {"components": []}
                    try:
                        async with httpx.AsyncClient(timeout=30) as client:
                            gemini_resp = await client.post(
                                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                                json={"contents": [{"parts": [{"text": components_prompt}]}]}
                            )
                            gemini_json = gemini_resp.json()
                            text = gemini_json["candidates"][0]["content"]["parts"][0]["text"]
                            # Estrai JSON dalla risposta
                            json_match = re.search(r'\{.*\}', text, re.DOTALL)
                            if json_match:
                                components_data = json.loads(json_match.group())
                    except Exception as e:
                        print(f"Gemini components error: {e}")

                    return {
                        "success": True,
                        "modelUrl": model_url,
                        "requestId": request_id,
                        "prompt": prompt,
                        "components": components_data.get("components", [])
                    }

                elif status in ["FAILED", "CANCELLED"]:
                    raise Exception(f"Job {status}: {status_data}")

            raise Exception("Timeout: model generation took too long")

    except Exception as e:
        print(f"❌ generate-3d error: {e}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ═══════════════════════════════════════════════════════════════════════════
# FORGE v2 — GENERATIVE POINT CLOUD
# ═══════════════════════════════════════════════════════════════════════════

FORGE_V2_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-3.1-pro-preview"]

FORGE_V2_PROMPT = """Sei un ingegnere 3D CAD. Dato un oggetto, descrivi la sua struttura come un insieme di superfici parametriche.
Rispondi SOLO in JSON valido, nessun testo aggiuntivo, nessun markdown.

Il JSON deve avere:
{
  "surfaces": [
    {
      "type": "plane|cylinder|sphere|cone|extrusion|ring",
      "label": "nome del componente",
      "color": "#hex colore",
      "params": { ... parametri specifici per tipo ... }
    }
  ],
  "metadata": {"name": "nome oggetto", "description": "breve descrizione"}
}

TIPI DI SUPERFICIE E PARAMETRI:

"plane": superficie piatta
  params: {"origin": [x,y,z], "u_axis": [ux,uy,uz], "v_axis": [vx,vy,vz], "u_size": float, "v_size": float, "density": int}
  - origin: angolo di partenza
  - u_axis/v_axis: direzioni dei due lati (normalizzate)
  - u_size/v_size: dimensioni
  - density: punti per lato (10-30)

"cylinder": tubo/colonna
  params: {"center": [x,y,z], "axis": [ax,ay,az], "radius": float, "height": float, "segments": int, "rings": int, "open": bool}
  - segments: punti lungo la circonferenza (16-32)
  - rings: anelli lungo l'altezza (5-15)
  - open: true = solo superficie laterale, false = include tappi

"sphere": sfera/cupola
  params: {"center": [x,y,z], "radius": float, "segments": int, "rings": int, "phi_start": 0, "phi_end": 6.28, "theta_start": 0, "theta_end": 3.14}
  - phi/theta per sfere parziali (cupole, mezze sfere)

"cone": cono/tronco di cono
  params: {"base_center": [x,y,z], "axis": [ax,ay,az], "base_radius": float, "top_radius": float, "height": float, "segments": int, "rings": int}

"extrusion": profilo 2D estruso lungo un asse
  params: {"profile": [[x1,y1],[x2,y2],...], "extrude_axis": [ax,ay,az], "extrude_length": float, "density": int, "offset": [ox,oy,oz]}
  - profile: punti 2D del profilo da estrudere (minimo 6 punti, usa molti punti per curve)

"ring": anello/toro
  params: {"center": [x,y,z], "axis": [ax,ay,az], "major_radius": float, "minor_radius": float, "segments": int, "tube_segments": int}

REGOLE:
- Usa MOLTE superfici per dettagliare l'oggetto (minimo 15 per oggetti semplici, 30+ per complessi)
- Ogni dettaglio visibile deve essere una superficie separata: finestre, porte, maniglie, tubi, cavi, schermi, bottoni
- Density alta (20-30) per superfici grandi, bassa (8-12) per piccole
- Le coordinate devono essere normalizzate: l'oggetto deve stare in un cubo da -1 a 1
- Colori diversi per componenti diversi: struttura principale cyan #00ffff, dettagli #00ccff, accenti #ff8844
- Se l'oggetto NON ESISTE nella realtà, immaginalo combinando elementi reali in modo plausibile
- REGOLA IMPORTANTE PER AMBIENTI INTERNI: quando l'utente chiede un ambiente (stanza, sala, laboratorio, cucina, ufficio, ecc.) NON generare un cubo chiuso di pareti. Genera SOLO:
  * Il pavimento (1 plane orizzontale in basso)
  * Massimo 2 pareti posteriori (back wall + 1 side wall) come riferimento spaziale
  * MAI il soffitto
  * MAI 4 pareti chiuse
  * Tutti gli oggetti interni con massimo dettaglio (mobili, attrezzature, strumenti, monitor, lampade, ecc.)
  L'utente deve poter vedere DENTRO l'ambiente come un modellino aperto

ESEMPIO per "tavolo":
{"surfaces": [
  {"type": "plane", "label": "Piano tavolo", "color": "#00ffff", "params": {"origin": [-0.5, 0.7, -0.3], "u_axis": [1,0,0], "v_axis": [0,0,1], "u_size": 1.0, "v_size": 0.6, "density": 20}},
  {"type": "cylinder", "label": "Gamba 1", "color": "#00ccff", "params": {"center": [-0.4, 0, -0.2], "axis": [0,1,0], "radius": 0.03, "height": 0.7, "segments": 12, "rings": 8, "open": true}},
  {"type": "cylinder", "label": "Gamba 2", "color": "#00ccff", "params": {"center": [0.4, 0, -0.2], "axis": [0,1,0], "radius": 0.03, "height": 0.7, "segments": 12, "rings": 8, "open": true}},
  {"type": "cylinder", "label": "Gamba 3", "color": "#00ccff", "params": {"center": [-0.4, 0, 0.2], "axis": [0,1,0], "radius": 0.03, "height": 0.7, "segments": 12, "rings": 8, "open": true}},
  {"type": "cylinder", "label": "Gamba 4", "color": "#00ccff", "params": {"center": [0.4, 0, 0.2], "axis": [0,1,0], "radius": 0.03, "height": 0.7, "segments": 12, "rings": 8, "open": true}}
], "metadata": {"name": "Table", "description": "Simple four-legged table"}}"""



@app.post("/api/forge-v2/generate")
async def forge_v2_generate(request: Request):
    """FORGE v2 — Genera point cloud 3D con Gemini Flash"""
    import time as _time
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt required")

        if not GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="Gemini API key not configured")

        print(f"\n⚡ FORGE v2: '{prompt}'")

        # Helper: chiama un modello Gemini
        async def call_gemini(model_name, payload, timeout_sec=120):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_sec, connect=15.0)) as c:
                return await c.post(url, headers={"Content-Type": "application/json"}, json=payload)

        # Step 1: Traduci il prompt in inglese (prova tutti i modelli)
        optimized_prompt = prompt
        for model in FORGE_V2_MODELS:
            try:
                t0 = _time.time()
                opt_resp = await call_gemini(model, {
                    "contents": [{"parts": [{"text": f"Translate to English and make it a detailed 3D object description (max 40 words, focus on shape and structure): {prompt}"}]}]
                }, timeout_sec=20)
                if opt_resp.status_code == 200:
                    opt_json = opt_resp.json()
                    optimized_prompt = opt_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    print(f"📝 Prompt EN [{model}] ({_time.time()-t0:.1f}s): {optimized_prompt}")
                    break
                elif opt_resp.status_code == 429:
                    print(f"⚠️ Translation [{model}] rate limited, trying next...")
                    continue
                else:
                    print(f"⚠️ Translation [{model}] HTTP {opt_resp.status_code}")
                    break
            except Exception as e:
                print(f"⚠️ Translation [{model}] error: {e}")
                continue

        # Step 2: Genera point cloud (prova tutti i modelli con fallback)
        used_model = None
        response = None
        t1 = _time.time()
        gen_payload = {
            "contents": [
                {"role": "user", "parts": [{"text": f"{FORGE_V2_PROMPT}\n\nOggetto da generare: {optimized_prompt}\n\nGENERA SOLO IL JSON:"}]}
            ],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 8192,
                "topP": 0.9
            }
        }

        for model in FORGE_V2_MODELS:
            print(f"🔄 Trying {model}...")
            try:
                resp = await call_gemini(model, gen_payload)
                elapsed = _time.time() - t1
                print(f"📥 [{model}] Status: {resp.status_code} ({elapsed:.1f}s)")
                if resp.status_code == 200:
                    response = resp
                    used_model = model
                    break
                elif resp.status_code == 429:
                    print(f"⚠️ [{model}] rate limited, trying next...")
                    continue
                else:
                    print(f"❌ [{model}] error: {resp.text[:200]}")
                    response = resp
                    used_model = model
                    break
            except Exception as e:
                print(f"⚠️ [{model}] exception: {e}")
                continue

        if response is None or response.status_code != 200:
            detail = "All models rate limited or failed"
            if response:
                detail = f"Gemini error: {response.text[:200]}"
            raise HTTPException(status_code=response.status_code if response else 503, detail=detail)

        elapsed = _time.time() - t1

        data = response.json()

        if "candidates" not in data or len(data["candidates"]) == 0:
            print(f"❌ Empty candidates: {json.dumps(data)[:500]}")
            raise HTTPException(status_code=500, detail="Empty response")

        candidate = data["candidates"][0]
        if "content" not in candidate:
            reason = candidate.get("finishReason", "unknown")
            print(f"❌ Blocked: {reason}")
            raise HTTPException(status_code=500, detail=f"Blocked: {reason}")

        response_text = candidate["content"]["parts"][0]["text"].strip()
        print(f"📝 Response: {len(response_text)} chars")
        print(f"📝 First 200: {response_text[:200]}")

        # Pulisci markdown
        if response_text.startswith("```"):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
            response_text = response_text.strip()

        # Parse JSON
        def repair_truncated_json(text):
            """Tenta di riparare JSON troncato chiudendo brackets/braces aperti"""
            # Rimuovi virgole finali prima di ] o }
            text = re.sub(r',\s*$', '', text.rstrip())
            # Rimuovi valori troncati (es. "[0.5, 0." → "[0.5")
            text = re.sub(r',\s*\[?[\d.\-]*$', '', text)
            text = re.sub(r',\s*"[^"]*$', '', text)
            # Conta brackets aperti
            opens = text.count('[') - text.count(']')
            braces = text.count('{') - text.count('}')
            text += ']' * max(0, opens) + '}' * max(0, braces)
            return text

        try:
            point_cloud = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parse error: {e}")
            # Prova a riparare JSON troncato
            try:
                repaired = repair_truncated_json(response_text)
                point_cloud = json.loads(repaired)
                print(f"🔧 JSON repaired OK ({len(repaired)} chars)")
            except json.JSONDecodeError:
                # Fallback: estrai con regex
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    try:
                        point_cloud = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        repaired2 = repair_truncated_json(json_match.group())
                        point_cloud = json.loads(repaired2)
                        print(f"🔧 JSON regex+repair OK")
                else:
                    raise HTTPException(status_code=500, detail="Invalid JSON from AI")

        # Validazione: formato parametrico con surfaces
        surfaces = point_cloud.get("surfaces", [])
        metadata = point_cloud.get("metadata", {})

        if not surfaces:
            raise HTTPException(status_code=500, detail="No surfaces in AI response")

        print(f"🔹 AI raw: {len(surfaces)} surfaces ({elapsed:.1f}s)")
        for s in surfaces:
            print(f"   └─ {s.get('type','?')}: {s.get('label','?')} ({s.get('color','#00ffff')})")

        return {
            "success": True,
            "surfaces": surfaces,
            "metadata": metadata,
            "engine": used_model or FORGE_V2_MODELS[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ FORGE v2 error: {type(e).__name__}: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": f"{type(e).__name__}: {e}"})


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "5.0 HYBRID",
        "system": "Component-Based 3D Assembly",
        "openai": bool(OPENAI_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "model": GEMINI_MODEL
    }


@app.get("/test-gemini")
async def test_gemini():
    if not GEMINI_API_KEY:
        return {"error": "GEMINI_API_KEY not set"}
    
    try:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": "Rispondi solo: OK"}]}]},
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return {"status": "ok", "model": GEMINI_MODEL, "response": text}
            else:
                return {"status": "error", "code": response.status_code}
    except Exception as e:
        return {"status": "error", "exception": str(e)}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 PINGIPOOL Backend v5 HYBRID")
    print("="*60)
    print(f"🤖 AI Model: {GEMINI_MODEL}")
    print("🧩 System: Component-Based 3D Assembly")
    print("📦 Components: cube, cylinder, sphere, cone, pyramid,")
    print("              roof, window, door, stairs, grid,")
    print("              torus, capsule, hexagon, arc")
    print("="*60)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)