import React, { useRef, useMemo, useEffect } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera } from '@react-three/drei'
import * as THREE from 'three'
import { usePHSEStore } from '../store/usePHSEStore'

interface TerrainMeshProps {
  demData: number[][];
  colorMapData: number[][];
  activeLayerName: string;
}

const TerrainMesh: React.FC<TerrainMeshProps> = ({ demData, colorMapData, activeLayerName }) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const geomRef = useRef<THREE.BufferGeometry>(null);

  const height = demData.length;
  const width = demData[0].length;

  // 1. Generate Vertex Coordinates based on DEM elevation
  const vertexElevation = useMemo(() => {
    const arr = new Float32Array(width * height);
    let idx = 0;
    // Find min/max for normalization
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
    const range = max - min || 1.0;

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const val = demData[y][x];
        // Normalize elevation to a nice 3D viewing scale (-10 to 10)
        arr[idx++] = val === -9999.0 ? -5 : ((val - min) / range) * 8 - 4;
      }
    }
    return arr;
  }, [demData, width, height]);

  // 2. Generate Color Texture Canvas to drape over the mesh
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d')!;

    // Color mapper based on active layer values
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
          // No data: dark gray
          imgData.data[offset] = 17;
          imgData.data[offset + 1] = 24;
          imgData.data[offset + 2] = 39;
          imgData.data[offset + 3] = 255;
          continue;
        }

        const normalized = (val - minVal) / rangeVal;

        // Apply distinct color gradients based on selected layer
        if (activeLayerName === 'geo_map') {
          // Discrete geological classification color palette
          if (val === 1.0) { // Pure Water Ice
            imgData.data[offset] = 56;   // R
            imgData.data[offset + 1] = 189; // G
            imgData.data[offset + 2] = 248; // B (Sky blue)
          } else if (val === 2.0) { // Mixture
            imgData.data[offset] = 129;
            imgData.data[offset + 1] = 140;
            imgData.data[offset + 2] = 248; // Indigo
          } else if (val === 3.0) { // Blocky Ejecta
            imgData.data[offset] = 245;
            imgData.data[offset + 1] = 158;
            imgData.data[offset + 2] = 11;  // Amber
          } else if (val === 4.0) { // Pyroclastic
            imgData.data[offset] = 168;
            imgData.data[offset + 1] = 85;
            imgData.data[offset + 2] = 247; // Purple
          } else { // Regolith
            imgData.data[offset] = 107;
            imgData.data[offset + 1] = 114;
            imgData.data[offset + 2] = 128; // Gray
          }
        } else if (activeLayerName.startsWith('prob_')) {
          // Scientific cyan hot intensity scale for probability
          imgData.data[offset] = Math.floor(normalized * 56);
          imgData.data[offset + 1] = Math.floor(normalized * 189);
          imgData.data[offset + 2] = Math.floor(normalized * 248);
        } else if (activeLayerName === 'hazard') {
          // Warning red intensity scale for hazard
          imgData.data[offset] = Math.floor(normalized * 220);
          imgData.data[offset + 1] = Math.floor((1 - normalized) * 100);
          imgData.data[offset + 2] = 50;
        } else {
          // Standard scientific grayscale / cool tone default
          const intensity = Math.floor(normalized * 255);
          imgData.data[offset] = Math.floor(intensity * 0.4);
          imgData.data[offset + 1] = Math.floor(intensity * 0.7);
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

  // 3. Update geometry vertices dynamically
  useEffect(() => {
    if (geomRef.current) {
      const positionAttr = geomRef.current.attributes.position;
      const count = positionAttr.count;

      for (let i = 0; i < count; i++) {
        // Map plane grid coordinate to flat index
        const px = i % width;
        const py = Math.floor(i / width);
        const dataIdx = py * width + px;
        const elevation = vertexElevation[dataIdx];
        
        // Update Z coordinate of plane geometry
        positionAttr.setZ(i, elevation);
      }
      positionAttr.needsUpdate = true;
      geomRef.current.computeVertexNormals();
    }
  }, [vertexElevation, width, height]);

  return (
    <mesh ref={meshRef} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry ref={geomRef} args={[20, 20, width - 1, height - 1]} />
      <meshStandardMaterial 
        map={texture} 
        roughness={0.7} 
        metalness={0.1} 
        wireframe={false} 
        side={THREE.DoubleSide}
      />
    </mesh>
  );
};

// Rover Traversal Path & Landing Overlay Components
interface OverlaysProps {
  demData: number[][];
  landingX: number;
  landingY: number;
  roverPath: [number, number][];
}

const Overlays: React.FC<OverlaysProps> = ({ demData, landingX, landingY, roverPath }) => {
  const height = demData.length;
  const width = demData[0].length;

  const get3DCoords = (gridX: number, gridY: number): THREE.Vector3 => {
    // Map grid (0 to width) to R3F plane coordinates (-10 to 10)
    const rx = (gridX / width) * 20 - 10;
    const ry = -(gridY / height) * 20 + 10; // Flip Y for WebGL texture coordinate convention
    
    // Elevate slightly above the terrain mesh surface (offset of 0.2)
    const val = demData[gridY]?.[gridX] ?? -9999.0;
    
    // Normalize elevation scale
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
    return new THREE.Vector3(rx, z, ry);
  };

  const pathPoints = useMemo(() => {
    if (!roverPath || roverPath.length === 0) return [];
    return roverPath.map(([px, py]) => get3DCoords(px, py));
  }, [roverPath, demData]);

  const landingPoint = useMemo(() => {
    return get3DCoords(landingX, landingY);
  }, [landingX, landingY, demData]);

  // Glowing marker animation
  const markerRef = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (markerRef.current) {
      const s = 1.0 + Math.sin(clock.getElapsedTime() * 5) * 0.15;
      markerRef.current.scale.set(s, s, s);
    }
  });

  return (
    <group>
      {/* 3D Landing Marker */}
      {landingPoint && (
        <mesh ref={markerRef} position={landingPoint}>
          <sphereGeometry args={[0.25, 16, 16]} />
          <meshBasicMaterial color="#38bdf8" />
        </mesh>
      )}

      {/* 3D Rover Traversal Path line strip */}
      {pathPoints.length > 0 && (
        <line>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              args={[new Float32Array(pathPoints.flatMap(p => [p.x, p.y, p.z])), 3]}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#facc15" linewidth={2} />
        </line>
      )}
    </group>
  );
};

export const ThreeViewer: React.FC = () => {
  const activeLayer = usePHSEStore((state) => state.activeLayer);
  const results = usePHSEStore((state) => state.pipelineResults);

  // Fallback data structure if pipeline hasn't run
  const demData = useMemo(() => {
    return results?.dem_layer?.data ?? null;
  }, [results]);

  const colorMapData = useMemo(() => {
    // Drape active selected layer values
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

  if (!demData || !colorMapData) {
    return (
      <div className="flex items-center justify-center h-full bg-[#0d1117] border border-white/5 rounded-lg text-gray-500 italic text-sm">
        Awaiting 3D Terrain Data... Click Recalculate to generate.
      </div>
    );
  }

  return (
    <div className="relative w-full h-full bg-[#090b0e] border border-white/5 rounded-lg overflow-hidden shadow-2xl">
      <Canvas>
        <PerspectiveCamera makeDefault position={[0, 15, 18]} fov={50} />
        <ambientLight intensity={0.4} />
        <directionalLight position={[10, 20, 10]} intensity={1.0} castShadow />
        <directionalLight position={[-10, 10, -10]} intensity={0.3} />
        
        <TerrainMesh 
          demData={demData} 
          colorMapData={colorMapData} 
          activeLayerName={activeLayer} 
        />

        {results && (
          <Overlays 
            demData={demData}
            landingX={results.landing_x}
            landingY={results.landing_y}
            roverPath={results.rover_path}
          />
        )}

        <OrbitControls 
          enableDamping 
          dampingFactor={0.05} 
          maxPolarAngle={Math.PI / 2.1} 
          minDistance={5} 
          maxDistance={35} 
        />
      </Canvas>

      {/* Floating 3D legend overlay */}
      <div className="absolute bottom-4 left-4 p-3 bg-[#161b22]/90 backdrop-blur-md border border-white/5 rounded-md text-xxs font-mono space-y-1 text-gray-400 select-none pointer-events-none">
        <div className="text-white font-bold mb-1 tracking-wider uppercase">3D Drape Overlay</div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-sky-400" />
          <span>Landing Recommendation</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded bg-yellow-400" />
          <span>A* Rover Traversal Path</span>
        </div>
        <div className="text-[10px] text-gray-500 mt-2">Active: {activeLayer.toUpperCase()} Map</div>
      </div>
    </div>
  );
};
