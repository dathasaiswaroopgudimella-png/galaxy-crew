import React, { useRef, useMemo, useEffect, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import { usePHSEStore } from '../../stores/usePHSEStore'
import { Eye, Shield, Camera, Bookmark, Navigation, Scale, Compass } from 'lucide-react'

interface TerrainMeshProps {
  demData: number[][];
  colorMapData: number[][];
  activeLayerName: string;
  opacity: number;
  onHoverPoint: (x: number, y: number, elevation: number) => void;
  onClickPoint: (point: THREE.Vector3 | null) => void;
}

const TerrainMesh: React.FC<TerrainMeshProps> = ({ 
  demData, 
  colorMapData, 
  activeLayerName,
  opacity,
  onHoverPoint,
  onClickPoint
}) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const geomRef = useRef<THREE.BufferGeometry>(null);

  const height = demData.length;
  const width = demData[0].length;

  const bounds = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const val = demData[y][x];
        if (val !== -9999.0) {
          if (val < min) min = val;
          if (val > max) max = val;
        }
      }
    }
    return { min, max, range: max - min || 1.0 };
  }, [demData, width, height]);

  const vertexElevation = useMemo(() => {
    const arr = new Float32Array(width * height);
    let idx = 0;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const val = demData[y][x];
        arr[idx++] = val === -9999.0 ? -5 : ((val - bounds.min) / bounds.range) * 8 - 4;
      }
    }
    return arr;
  }, [demData, bounds, width, height]);

  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d')!;

    let minVal = Infinity;
    let maxVal = -Infinity;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const val = colorMapData[y][x];
        if (val !== -9999.0) {
          if (val < minVal) minVal = val;
          if (val > maxVal) maxVal = val;
        }
      }
    }
    const rangeVal = maxVal - minVal || 1.0;

    const imgData = ctx.createImageData(width, height);
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const val = colorMapData[y][x];
        const offset = (y * width + x) * 4;

        if (val === -9999.0) {
          imgData.data[offset] = 10;
          imgData.data[offset + 1] = 12;
          imgData.data[offset + 2] = 18;
          imgData.data[offset + 3] = 255;
          continue;
        }

        const normalized = (val - minVal) / rangeVal;

        if (activeLayerName === 'geo_map') {
          if (val === 1.0) { // Pure Ice
            imgData.data[offset] = 0;
            imgData.data[offset + 1] = 229;
            imgData.data[offset + 2] = 255;
          } else if (val === 2.0) { // Mixture
            imgData.data[offset] = 37;
            imgData.data[offset + 1] = 99;
            imgData.data[offset + 2] = 235;
          } else if (val === 3.0) { // Ejecta
            imgData.data[offset] = 245;
            imgData.data[offset + 1] = 158;
            imgData.data[offset + 2] = 11;
          } else if (val === 4.0) { // Pyroclastic
            imgData.data[offset] = 168;
            imgData.data[offset + 1] = 85;
            imgData.data[offset + 2] = 247;
          } else { // Regolith
            imgData.data[offset] = 71;
            imgData.data[offset + 1] = 85;
            imgData.data[offset + 2] = 105;
          }
        } else if (activeLayerName.startsWith('prob_')) {
          imgData.data[offset] = Math.floor(normalized * 0);
          imgData.data[offset + 1] = Math.floor(normalized * 229);
          imgData.data[offset + 2] = Math.floor(normalized * 255);
        } else if (activeLayerName === 'hazard') {
          imgData.data[offset] = Math.floor(normalized * 239);
          imgData.data[offset + 1] = Math.floor((1 - normalized) * 68);
          imgData.data[offset + 2] = 68;
        } else {
          // Standard grayscale/blue telemetry map draping
          const intensity = Math.floor(normalized * 255);
          imgData.data[offset] = Math.floor(intensity * 0.15);
          imgData.data[offset + 1] = Math.floor(intensity * 0.65);
          imgData.data[offset + 2] = intensity;
        }
        imgData.data[offset + 3] = 255;
      }
    }
    ctx.putImageData(imgData, 0, 0);

    const tex = new THREE.CanvasTexture(canvas);
    tex.needsUpdate = true;

    return tex;
  }, [colorMapData, activeLayerName, width, height]);

  useEffect(() => {
    return () => {
      texture.dispose();
    };
  }, [texture]);

  useEffect(() => {
    if (geomRef.current) {
      const positionAttr = geomRef.current.attributes.position;
      const count = positionAttr.count;

      for (let i = 0; i < count; i++) {
        const px = i % width;
        const py = Math.floor(i / width);
        const dataIdx = py * width + px;
        positionAttr.setZ(i, vertexElevation[dataIdx]);
      }
      positionAttr.needsUpdate = true;
      geomRef.current.computeVertexNormals();
    }
  }, [vertexElevation, width, height]);

  const handlePointerMove = (e: any) => {
    e.stopPropagation();
    if (e.uv) {
      const gridX = Math.floor(e.uv.x * (width - 1));
      const gridY = Math.floor((1 - e.uv.y) * (height - 1));
      const rawElev = demData[gridY]?.[gridX] ?? 0.0;
      onHoverPoint(gridX, gridY, rawElev);
    }
  };

  const handlePointerClick = (e: any) => {
    e.stopPropagation();
    if (e.point) {
      onClickPoint(e.point);
    }
  };

  return (
    <mesh 
      ref={meshRef} 
      rotation={[-Math.PI / 2, 0, 0]}
      onPointerMove={handlePointerMove}
      onPointerDown={handlePointerClick}
    >
      <planeGeometry ref={geomRef} args={[20, 20, width - 1, height - 1]} />
      <meshStandardMaterial 
        map={texture} 
        transparent
        opacity={opacity}
        roughness={0.8} 
        metalness={0.2} 
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

interface OverlaysProps {
  demData: number[][];
  landingX: number;
  landingY: number;
  roverPath: [number, number][];
  playbackStep: number;
}

const Overlays: React.FC<OverlaysProps> = ({ demData, landingX, landingY, roverPath, playbackStep }) => {
  const height = demData.length;
  const width = demData[0].length;

  const get3DCoords = (gridX: number, gridY: number): THREE.Vector3 => {
    const rx = (gridX / width) * 20 - 10;
    const ry = -(gridY / height) * 20 + 10;
    const val = demData[gridY]?.[gridX] ?? -9999.0;
    
    let min = Infinity, max = -Infinity;
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const d = demData[y][x];
        if (d !== -9999.0) {
          if (d < min) min = d;
          if (d > max) max = d;
        }
      }
    }
    const z = val === -9999.0 ? -4.8 : ((val - min) / (max - min || 1)) * 8 - 3.8;
    return new THREE.Vector3(rx, z + 0.15, ry);
  };

  const pathPoints = useMemo(() => {
    if (!roverPath || roverPath.length === 0) return [];
    
    let pathLen = roverPath.length;
    if (playbackStep === 0) pathLen = 0;
    else if (playbackStep === 1) pathLen = Math.floor(roverPath.length / 2);
    
    return roverPath.slice(0, pathLen).map(([px, py]) => get3DCoords(px, py));
  }, [roverPath, demData, playbackStep]);

  const landingPoint = useMemo(() => {
    return get3DCoords(landingX, landingY);
  }, [landingX, landingY, demData]);

  const markerRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (markerRef.current) {
      const s = 1.0 + Math.sin(clock.getElapsedTime() * 5) * 0.2;
      markerRef.current.scale.set(s, s, s);
    }
  });

  return (
    <group>
      {landingPoint && (
        <mesh ref={markerRef} position={landingPoint}>
          <sphereGeometry args={[0.22, 16, 16]} />
          <meshBasicMaterial color="#00e5ff" />
        </mesh>
      )}

      {pathPoints.length > 0 && (
        <line>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[new Float32Array(pathPoints.flatMap(p => [p.x, p.y, p.z])), 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#fbbf24" linewidth={3.0} />
        </line>
      )}
    </group>
  );
};

interface CameraControllerProps {
  bookmark: 'overview' | 'landing' | 'traverse' | null;
  onComplete: () => void;
}

const CameraController: React.FC<CameraControllerProps> = ({ bookmark, onComplete }) => {
  const { camera } = useThree();

  useEffect(() => {
    if (!bookmark) return;

    let targetPos = new THREE.Vector3(0, 14, 17);
    let targetLook = new THREE.Vector3(0, 0, 0);

    if (bookmark === 'landing') {
      targetPos.set(2.5, 3.5, 2.5);
      targetLook.set(0, -0.8, 0);
    } else if (bookmark === 'traverse') {
      targetPos.set(-4, 7, 9);
      targetLook.set(0.8, -1.8, -0.8);
    }

    camera.position.copy(targetPos);
    camera.lookAt(targetLook);
    onComplete();
  }, [bookmark, camera]);

  return null;
};

export const ThreeViewer: React.FC = () => {
  const activeLayer = usePHSEStore((state) => state.activeLayer);
  const results = usePHSEStore((state) => state.pipelineResults);
  const hoverCoords = usePHSEStore((state) => state.hoverCoords);
  const setHoverCoords = usePHSEStore((state) => state.setHoverCoords);
  const setHoverDetails = usePHSEStore((state) => state.setHoverDetails);
  const playbackStep = usePHSEStore((state) => state.playbackStep);

  const [opacity, setOpacity] = useState<number>(0.85);
  const [cameraBookmark, setCameraBookmark] = useState<'overview' | 'landing' | 'traverse' | null>(null);
  const [measuring, setMeasuring] = useState(false);
  const [measurePoints, setMeasurePoints] = useState<THREE.Vector3[]>([]);
  const [measuredDistance, setMeasuredDistance] = useState<number | null>(null);

  const demData = useMemo(() => {
    return results?.dem_layer?.data ?? null;
  }, [results]);

  const colorMapData = useMemo(() => {
    if (!results) return null;
    if (activeLayer === 'dem') return results.dem_layer?.data;
    if (activeLayer === 'cpr') return results.cpr_layer?.data;
    if (activeLayer === 'dop') return results.dop_layer?.data;
    if (activeLayer === 'hazard') return results.hazard_layer?.data;
    if (activeLayer === 'geo_map') return results.geo_map?.data;
    if (activeLayer === 'entropy') return results.entropy_layer?.data;
    if (activeLayer.startsWith('prob_')) {
      const key = activeLayer.replace('prob_', '');
      return results.probability_layers?.[key]?.data;
    }
    return results.dem_layer?.data;
  }, [results, activeLayer]);

  const handleHoverPoint = async (x: number, y: number, elevation: number) => {
    if (hoverCoords?.x === x && hoverCoords?.y === y) return;
    setHoverCoords({ x, y });
    
    try {
      const res = await fetch(`/api/pixel?x=${x}&y=${y}`);
      const details = await res.json();
      setHoverDetails(details);
    } catch (e) {
      setHoverDetails({
        x, y, dem: elevation, cpr: 0.5, dop: 0.5, hazard: 0.1,
        probabilities: { pure_water_ice: 0.1, ice_regolith_mixture: 0.1, blocky_ejecta: 0.2, pyroclastic_deposits: 0.1, dry_regolith: 0.5 }
      });
    }
  };

  const handleMeshClick = (point: THREE.Vector3 | null) => {
    if (!measuring || !point) return;

    const newPoints = [...measurePoints, point];
    if (newPoints.length > 2) {
      setMeasurePoints([point]);
      setMeasuredDistance(null);
    } else {
      setMeasurePoints(newPoints);
      if (newPoints.length === 2) {
        const dist = newPoints[0].distanceTo(newPoints[1]) * 12.5; 
        setMeasuredDistance(dist);
      }
    }
  };

  if (!demData || !colorMapData) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#05070a]/60 border border-white/5 rounded text-white/30 italic text-[10px] select-none font-mono uppercase tracking-widest">
        <Navigation size={20} className="text-white/20 animate-pulse mb-2" />
        <span>Awaiting Lunar Workspace Telemetry... Run Pipeline.</span>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[#030508] border border-cyan-500/20 rounded-md overflow-hidden shadow-[0_0_25px_rgba(6,182,212,0.05)]">
      {/* HUD target ticks on the canvas boundaries */}
      <div className="absolute top-2 left-2 text-[9px] text-cyan-400/30 select-none pointer-events-none font-mono uppercase tracking-widest">Target Mode: Lunar Surface</div>
      <div className="absolute top-2 right-2 text-[9px] text-cyan-400/30 select-none pointer-events-none font-mono uppercase tracking-widest">Scale: 1:1250</div>
      
      {/* 3D Canvas */}
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 14, 17]} fov={50} />
        <ambientLight intensity={0.45} />
        <directionalLight position={[12, 18, 12]} intensity={1.1} />
        <directionalLight position={[-12, 10, -12]} intensity={0.2} />
        
        <TerrainMesh 
          demData={demData} 
          colorMapData={colorMapData} 
          activeLayerName={activeLayer} 
          opacity={opacity}
          onHoverPoint={handleHoverPoint}
          onClickPoint={handleMeshClick}
        />

        {results && (
          <Overlays 
            demData={demData}
            landingX={results.landing_x}
            landingY={results.landing_y}
            roverPath={results.rover_path}
            playbackStep={playbackStep}
          />
        )}

        {measurePoints.length === 2 && (
          <line>
            <bufferGeometry attach="geometry">
              <bufferAttribute
                attach="attributes-position"
                args={[new Float32Array(measurePoints.flatMap(p => [p.x, p.y + 0.1, p.z])), 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial attach="material" color="#f87171" linewidth={2.5} />
          </line>
        )}

        <CameraController 
          bookmark={cameraBookmark} 
          onComplete={() => setCameraBookmark(null)} 
        />

        <OrbitControls 
          enableDamping 
          dampingFactor={0.05} 
          maxPolarAngle={Math.PI / 2.1} 
          minDistance={4} 
          maxDistance={30} 
        />
      </Canvas>

      {/* Opacity slider toolbar */}
      <div className="absolute top-3.5 left-3.5 flex items-center gap-2 p-1.5 bg-[#0c0e14]/90 backdrop-blur-md border border-white/10 rounded shadow-md select-none font-mono">
        <span className="text-[8px] text-white/50 font-bold uppercase tracking-widest flex items-center gap-1">
          <Eye size={11} />
          <span>Opacity:</span>
        </span>
        <input 
          type="range" 
          min="0.2" 
          max="1.0" 
          step="0.05"
          value={opacity}
          onChange={(e) => setOpacity(parseFloat(e.target.value))}
          className="w-16 accent-cyan-500 h-[2px] bg-white/10 rounded appearance-none cursor-pointer"
        />
        <span className="text-[8px] text-white font-bold">{Math.floor(opacity * 100)}%</span>
      </div>

      {/* Floating Camera Bookmarks Toolbar */}
      <div className="absolute top-3.5 right-3.5 flex gap-1 p-1 bg-[#0c0e14]/90 backdrop-blur-md border border-white/10 rounded shadow-md select-none">
        <button
          onClick={() => setCameraBookmark('overview')}
          className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-white transition-colors cursor-pointer"
          title="Zoom to Overview View"
        >
          <Bookmark size={11} />
        </button>
        <button
          onClick={() => setCameraBookmark('landing')}
          className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-white transition-colors cursor-pointer"
          title="Zoom to Lander"
        >
          <Camera size={11} />
        </button>
        <button
          onClick={() => setCameraBookmark('traverse')}
          className="p-1 hover:bg-white/5 rounded text-white/40 hover:text-white transition-colors cursor-pointer"
          title="Zoom to Path"
        >
          <Compass size={11} />
        </button>
      </div>

      {/* Measurement tools overlay */}
      <div className="absolute bottom-3.5 right-3.5 flex flex-col items-end gap-1.5 select-none font-mono">
        <button
          onClick={() => {
            setMeasuring(!measuring);
            setMeasurePoints([]);
            setMeasuredDistance(null);
          }}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded border text-[8px] font-bold tracking-widest uppercase shadow-md transition-all cursor-pointer ${
            measuring 
              ? 'bg-rose-500/20 text-rose-400 border-rose-500/40' 
              : 'bg-[#0c0e14]/90 text-white/50 border-white/10 hover:text-white'
          }`}
        >
          <Scale size={11} />
          <span>{measuring ? 'Exit Measure' : 'Measure'}</span>
        </button>
        {measuredDistance !== null && (
          <div className="p-1.5 bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded text-[8px] font-bold">
            Distance: {measuredDistance.toFixed(2)} m
          </div>
        )}
      </div>

      {/* Scientific Overlay Legend HUD */}
      <div className="absolute bottom-3.5 left-3.5 p-2.5 bg-[#0c0e14]/90 backdrop-blur-md border border-white/10 rounded text-[8px] font-mono space-y-1 text-white/50 select-none pointer-events-none shadow-md">
        <div className="text-white font-bold mb-1 tracking-widest uppercase flex items-center gap-1">
          <Shield size={10} className="text-cyan-400" />
          <span>Targets</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
          <span>Lander Target</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
          <span>Rover Traverse</span>
        </div>
        <div className="text-[7px] text-white/30 uppercase mt-1">Sensor: {activeLayer.toUpperCase()}</div>
      </div>
    </div>
  );
};
