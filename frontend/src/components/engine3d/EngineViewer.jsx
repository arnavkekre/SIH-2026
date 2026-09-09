/**
 * EngineViewer — AeroTwin 3D Digital Twin Component
 *
 * Ports the full Three.js engine visualization from script.js into React.
 *
 * All original rendering code is preserved:
 *   - GLTFLoader + OrbitControls + RoomEnvironment
 *   - RPM-mapped animation speed
 *   - Vibration-driven engine shake / jitter
 *   - 4-cylinder combustion particle system with flame fronts
 *   - Cylinder stroke phase tracking (Power / Exhaust / Intake / Compression)
 *   - Pipe fluid flow animation (water, fuel, exhaust, heated water)
 *   - Transparent glass shell overlays
 *
 * CSV playback logic is REMOVED.
 * Telemetry values come from props (wired to Zustand store by parent).
 * Health status drives subtle 3D color tinting.
 *
 * Props:
 *   rpm          {number|null}   Engine RPM from backend telemetry
 *   vibration    {number|null}   Vibration G from backend telemetry
 *   healthStatus {string|null}   'HEALTHY' | 'WARNING' | 'DEGRADING' | 'CRITICAL'
 *   faultType    {string|null}   Top fault type string from backend inference
 *   className    {string}        Additional CSS classes for the container
 */

import React, { useEffect, useRef, useState, useCallback } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js'
import { RotateCcw, Maximize2, Play, Eye } from 'lucide-react'

// ─────────────────────────────────────────────────────────────
// CONSTANTS (preserved from script.js)
// ─────────────────────────────────────────────────────────────

const TELEMETRY_RPM_MIN = 900
const TELEMETRY_RPM_MAX = 3700
const VISUAL_RPM_MIN = 15
const VISUAL_RPM_MAX = 90

const PARTICLES_PER_CYL = 300
const LAYER_COUNT = 300
const GROW_FRACTION = 0.4
const EFFECT_SCALE = 4
const CYL_RADIUS = 2.2 * EFFECT_SCALE
const CYL_DEPTH = 2.0 * EFFECT_SCALE
const JITTER_INTERVAL = 0.06

const STROKE_COLORS = {
  power:       0xffffff,
  exhaust:     0x999999,
  intake:      0x3399ff,
  compression: 0xffaa33,
}
const STROKE_NAMES = {
  power: 'Power',
  exhaust: 'Exhaust',
  intake: 'Intake',
  compression: 'Compression',
}

const cylinderPairs = [[0, 1], [2, 3]]
const pairFireTime  = [0, 0.5]
const cylinderFireTime = [0, 0, 0, 0]
cylinderPairs.forEach((pair, pairIndex) => {
  pair.forEach((cyl) => { cylinderFireTime[cyl] = pairFireTime[pairIndex] })
})

// Model URL — served by backend StaticFiles mount
const MODEL_URL = import.meta.env.VITE_MODEL_URL || 'http://localhost:8000/3D_Models/rotax912engine.glb'

// ─────────────────────────────────────────────────────────────
// HEALTH STATUS → THREE.JS COLOR MAPPING
// ─────────────────────────────────────────────────────────────

const HEALTH_TINT_COLORS = {
  HEALTHY:   new THREE.Color(0x22c55e),   // green
  WARNING:   new THREE.Color(0xf59e0b),   // amber
  DEGRADING: new THREE.Color(0xf97316),   // orange
  CRITICAL:  new THREE.Color(0xef4444),   // red
}

function mapRpmToVisual(telemetryRpm) {
  if (telemetryRpm == null) return VISUAL_RPM_MIN
  const t = Math.min(1, Math.max(0, (telemetryRpm - TELEMETRY_RPM_MIN) / (TELEMETRY_RPM_MAX - TELEMETRY_RPM_MIN)))
  return VISUAL_RPM_MIN + t * (VISUAL_RPM_MAX - VISUAL_RPM_MIN)
}

// ─────────────────────────────────────────────────────────────
// TEXTURE FACTORIES (preserved from script.js)
// ─────────────────────────────────────────────────────────────

function makeSoftDotTexture() {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  grad.addColorStop(0.0, 'rgba(255,255,255,1)')
  grad.addColorStop(0.4, 'rgba(255,255,255,0.7)')
  grad.addColorStop(1.0, 'rgba(255,255,255,0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, size, size)
  const tex = new THREE.CanvasTexture(canvas)
  tex.needsUpdate = true
  return tex
}

function makeFlowTexture(hexColor) {
  const canvas = document.createElement('canvas')
  canvas.width = 128
  canvas.height = 128
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#111111'
  ctx.fillRect(0, 0, 128, 128)
  ctx.fillStyle = hexColor
  for (let i = 0; i < 128; i += 32) {
    ctx.fillRect(i, 0, 16, 128)
  }
  const tex = new THREE.CanvasTexture(canvas)
  tex.wrapS = THREE.RepeatWrapping
  tex.wrapT = THREE.RepeatWrapping
  return tex
}

// ─────────────────────────────────────────────────────────────
// COMPONENT
// ─────────────────────────────────────────────────────────────

export default function EngineViewer({
  rpm = null,
  vibration = null,
  healthStatus = null,
  faultType = null,
  className = '',
}) {
  const containerRef = useRef(null)
  const canvasRef    = useRef(null)

  // Three.js object refs (not state — don't trigger re-renders)
  const sceneRef         = useRef(null)
  const cameraRef        = useRef(null)
  const rendererRef      = useRef(null)
  const controlsRef      = useRef(null)
  const mixerRef         = useRef(null)
  const mainActionRef    = useRef(null)
  const engineModelRef   = useRef(null)
  const engineBasePosRef = useRef(null)
  const clockRef         = useRef(null)
  const animFrameRef     = useRef(null)
  const nativeAnimDurRef = useRef(0)

  // Mutable engine state refs (updated each frame from props)
  const engineRPMRef = useRef(VISUAL_RPM_MIN)

  // Engine part refs
  const propGearRef        = useRef(null)
  const fuelPumpGearRef    = useRef(null)
  const alternatorRef      = useRef(null)
  const crankFrontRef      = useRef(null)
  const fuelImpellerRef    = useRef(null)
  const waterImpellerRef   = useRef(null)

  // Combustion arrays (preserved from script.js)
  const combustionLightsRef = useRef([])
  const particleSystemsRef  = useRef([])
  const fireLayersRef       = useRef([])
  const fireBrightnessRef   = useRef([])
  const glowSpritesRef      = useRef([])
  const fluidMaterialsRef   = useRef([])

  // Jitter state refs
  const jitterCurrentRef = useRef(new THREE.Vector3())
  const jitterTargetRef  = useRef(new THREE.Vector3())
  const jitterTimerRef   = useRef(0)
  const firingPunchRef   = useRef({ 0: 0, 1: 0 })
  const shakeClockRef    = useRef(0)

  // UI state
  const [isLoaded,    setIsLoaded]    = useState(false)
  const [loadError,   setLoadError]   = useState(null)
  const [autoRotate,  setAutoRotate]  = useState(false)
  const [strokeNames, setStrokeNames] = useState(['--', '--', '--', '--'])

  // Props as refs (so the animation loop can read them without dependency issues)
  const rpmRef          = useRef(rpm)
  const vibrationRef    = useRef(vibration)
  const healthStatusRef = useRef(healthStatus)

  useEffect(() => { rpmRef.current = rpm }, [rpm])
  useEffect(() => { vibrationRef.current = vibration }, [vibration])
  useEffect(() => { healthStatusRef.current = healthStatus }, [healthStatus])

  // ─────────────────────────────────────────────────────────
  // THREE.JS INIT
  // ─────────────────────────────────────────────────────────

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // Scene
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    )
    camera.position.set(40, 20, 50)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(container.clientWidth, container.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    container.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Environment
    const pmremGenerator = new THREE.PMREMGenerator(renderer)
    scene.environment = pmremGenerator.fromScene(new RoomEnvironment(), 0.04).texture

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.05
    controlsRef.current = controls

    // Lights
    scene.add(new THREE.AmbientLight(0xffffff, 1.5))
    const dirLight = new THREE.DirectionalLight(0xffffff, 2)
    dirLight.position.set(10, 20, 10)
    scene.add(dirLight)

    // Clock
    clockRef.current = new THREE.Clock()

    // Textures
    const softDotTexture = makeSoftDotTexture()
    const waterTex       = makeFlowTexture('#00aaff')
    const fuelTex        = makeFlowTexture('#ffcc00')
    const heatWaterTex   = makeFlowTexture('#ff3300')
    const insideWaterTex = makeFlowTexture('#E68D2E')
    const exhaustTex     = makeFlowTexture('#999999')

    // ─────────────────────────────────────────────────────────
    // LOAD GLB
    // ─────────────────────────────────────────────────────────
    const loader = new GLTFLoader()
    loader.load(
      MODEL_URL,
      (gltf) => {
        const model = gltf.scene
        engineModelRef.current = model

        const mixer = new THREE.AnimationMixer(model)
        mixerRef.current = mixer

        if (gltf.animations.length > 0) {
          nativeAnimDurRef.current = gltf.animations[0].duration
          const targetRPS = engineRPMRef.current / 60
          mixer.timeScale = targetRPS * nativeAnimDurRef.current
        }

        gltf.animations.forEach((clip) => {
          mainActionRef.current = mixer.clipAction(clip)
          mainActionRef.current.play()
        })

        // Part references
        propGearRef.current      = model.getObjectByName('prop_gear')
        fuelPumpGearRef.current  = model.getObjectByName('fuel_pump_gear')
        alternatorRef.current    = model.getObjectByName('crankshaft_alternator_end')
        crankFrontRef.current    = model.getObjectByName('crankshaft_reduction_end')
        fuelImpellerRef.current  = model.getObjectByName('fuel_impeller')
        waterImpellerRef.current = model.getObjectByName('water_pump_impeller')

        const Case1 = model.getObjectByName('cylinder_head_case')
        const Case2 = model.getObjectByName('cylinder_head_case001')
        const Case3 = model.getObjectByName('cylinder_head_case002')
        const Case4 = model.getObjectByName('cylinder_head_case003')
        const Cover1 = model.getObjectByName('cylinder002')
        const Cover2 = model.getObjectByName('cylinder_head001')
        const Cover3 = model.getObjectByName('cylinder001')
        const Cover4 = model.getObjectByName('cylinderhead003')
        const Cover5 = model.getObjectByName('cylinder')
        const Cover6 = model.getObjectByName('cylinder003')
        const alternatorCover = model.getObjectByName('alternater')

        // Pipe fluid setup
        const waterPipeNames   = ['belowpipe1','belowpipe2','belowpipe3','belowpipe4']
        const fuelPipeNames    = ['fuel_pipe_left','fuel_pipe_right','fuelpipeinside1','fuelpipeinside2','fuelpipeinside3','fuelpipeinside4']
        const heatWaterNames   = ['abovepipe1','abovepipe2','abovepipe3','abovepipe4']
        const insideWaterNames = ['waterpipeinside1','waterpipeinside2','waterpipeinside3','waterpipeinside4']
        const exhaustNames     = ['exhaust1','exhaust2','exhaust3','exhaust4']

        function setupPipes(names, texture, speed) {
          names.forEach((name) => {
            const pipe = model.getObjectByName(name)
            if (pipe && pipe.material) {
              pipe.material = pipe.material.clone()
              pipe.material.map = texture
              pipe.material.emissiveMap = texture
              pipe.material.emissive = new THREE.Color(0xffffff)
              pipe.material.emissiveIntensity = 0.8
              fluidMaterialsRef.current.push({ mat: pipe.material, speed })
            }
          })
        }

        setupPipes(waterPipeNames, waterTex, 0.5)
        setupPipes(fuelPipeNames, fuelTex, 0.8)
        setupPipes(heatWaterNames, heatWaterTex, 0.8)
        setupPipes(insideWaterNames, insideWaterTex, 0.8)
        setupPipes(exhaustNames, exhaustTex, 0.8)

        // Glass shells
        function makeGlass(obj, opacity) {
          if (!obj) return
          obj.traverse((child) => {
            if (child.isMesh && child.material) {
              child.material = child.material.clone()
              child.material.transparent = true
              child.material.opacity = opacity
              child.material.depthWrite = false
            }
          })
        }

        const shellOpacity = 0.3
        const leftCase  = model.getObjectByName('engine_front1')
        const rightCase = model.getObjectByName('cylinder_case_right')
        const headCase  = model.getObjectByName('cylinder_case_left')

        makeGlass(leftCase, shellOpacity)
        makeGlass(rightCase, shellOpacity)
        makeGlass(headCase, shellOpacity)
        makeGlass(alternatorCover, shellOpacity)
        makeGlass(Case1, shellOpacity)
        makeGlass(Case2, shellOpacity)
        makeGlass(Case3, shellOpacity)
        makeGlass(Case4, shellOpacity)
        makeGlass(Cover1, shellOpacity)
        makeGlass(Cover2, shellOpacity)
        makeGlass(Cover3, shellOpacity)
        makeGlass(Cover4, shellOpacity)
        makeGlass(Cover5, shellOpacity)
        makeGlass(Cover6, shellOpacity)

        // Combustion particles + lights
        const cylinderNames = ['cylinder','cylinder001','cylinder002','cylinder003']

        const fireMaterial = new THREE.PointsMaterial({
          color: 0xffffff,
          map: softDotTexture,
          vertexColors: true,
          size: 3.2 * EFFECT_SCALE,
          transparent: true,
          opacity: 1.0,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        })

        const glowSpriteMaterial = new THREE.SpriteMaterial({
          map: softDotTexture,
          color: 0x3399ff,
          transparent: true,
          opacity: 0,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        })

        cylinderNames.forEach((name) => {
          const cyl = model.getObjectByName(name)
          if (!cyl) return

          const spark = new THREE.PointLight(0xff4400, 0, 25)
          spark.position.set(0, 2, 2.5)
          cyl.add(spark)
          combustionLightsRef.current.push(spark)

          const geometry = new THREE.BufferGeometry()
          const positions = new Float32Array(PARTICLES_PER_CYL * 3)
          const colors    = new Float32Array(PARTICLES_PER_CYL * 3)
          const layers    = new Float32Array(PARTICLES_PER_CYL)
          const brightness= new Float32Array(PARTICLES_PER_CYL)

          for (let i = 0; i < PARTICLES_PER_CYL; i++) {
            const theta = Math.random() * Math.PI * 2
            const rad   = CYL_RADIUS * Math.sqrt(Math.random())
            const depth = (Math.random() - 0.5) * CYL_DEPTH

            positions[i * 3]     = Math.cos(theta) * rad
            positions[i * 3 + 1] = depth
            positions[i * 3 + 2] = Math.sin(theta) * rad

            const normalizedR = rad / CYL_RADIUS
            layers[i]     = Math.min(LAYER_COUNT - 1, Math.floor(normalizedR * LAYER_COUNT))
            brightness[i] = 0.7 + Math.random() * 0.3
          }

          geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
          geometry.setAttribute('color',    new THREE.BufferAttribute(colors, 3))

          const particles = new THREE.Points(geometry, fireMaterial)
          particles.position.set(0, 2, 2.5)
          particles.visible = false
          cyl.add(particles)
          particleSystemsRef.current.push(particles)
          fireLayersRef.current.push(layers)
          fireBrightnessRef.current.push(brightness)

          const glow = new THREE.Sprite(glowSpriteMaterial.clone())
          glow.position.set(0, 2, 2.5)
          glow.scale.set(4, 4, 4)
          cyl.add(glow)
          glowSpritesRef.current.push(glow)
        })

        // Center the model
        const box    = new THREE.Box3().setFromObject(model)
        const center = box.getCenter(new THREE.Vector3())
        model.position.sub(center)
        engineBasePosRef.current = model.position.clone()

        scene.add(model)
        setIsLoaded(true)
      },
      undefined,
      (error) => {
        console.error('[EngineViewer] GLB load error:', error)
        setLoadError('Failed to load 3D engine model. Ensure the backend is running.')
      }
    )

    // ─────────────────────────────────────────────────────────
    // ANIMATION LOOP
    // ─────────────────────────────────────────────────────────

    const tmpColor   = new THREE.Color()
    const leadColor  = new THREE.Color(0xffffff)
    const bodyColor  = new THREE.Color(0xff6600)

    function updateFlameFront(cylIndex, t) {
      const particles   = particleSystemsRef.current[cylIndex]
      const layers      = fireLayersRef.current[cylIndex]
      const brightnessArr = fireBrightnessRef.current[cylIndex]
      const colorAttr   = particles.geometry.getAttribute('color')
      const colorArray  = colorAttr.array

      let growFront, burnFront
      if (t <= GROW_FRACTION) {
        growFront = (t / GROW_FRACTION) * LAYER_COUNT
        burnFront = -1
      } else {
        growFront = LAYER_COUNT
        burnFront = ((t - GROW_FRACTION) / (1 - GROW_FRACTION)) * LAYER_COUNT
      }

      for (let i = 0; i < layers.length; i++) {
        const layer = layers[i]
        const lit   = layer < growFront && layer >= burnFront

        if (!lit) {
          colorArray[i * 3] = colorArray[i * 3 + 1] = colorArray[i * 3 + 2] = 0
          continue
        }

        const isLeadingEdge = (growFront - layer) < 1.5 && burnFront < 0
        tmpColor.copy(isLeadingEdge ? leadColor : bodyColor)
        const b = brightnessArr[i]
        colorArray[i * 3]     = tmpColor.r * b
        colorArray[i * 3 + 1] = tmpColor.g * b
        colorArray[i * 3 + 2] = tmpColor.b * b
      }

      colorAttr.needsUpdate = true
    }

    const strokeNamesCopy = ['--', '--', '--', '--']

    function updateCylinderStroke(cylIndex, localPhase) {
      const light = combustionLightsRef.current[cylIndex]
      const fire  = particleSystemsRef.current[cylIndex]
      const glow  = glowSpritesRef.current[cylIndex]

      let strokeKey

      if (localPhase < 0.25) {
        strokeKey = 'power'
        const t = localPhase / 0.25
        fire.visible = true
        updateFlameFront(cylIndex, t)
        light.color.setHex(0xff5500)
        light.intensity = 90 * Math.max(0, 1 - t) * (1 - t)
        glow.material.opacity = 0
        if (t < 0.05) {
          const pairIndex = cylinderPairs.findIndex((pair) => pair.includes(cylIndex))
          if (pairIndex !== -1) {
            firingPunchRef.current[pairIndex] = 1.0
          }
        }
      } else if (localPhase < 0.5) {
        strokeKey = 'exhaust'
        const rel = (localPhase - 0.25) / 0.25
        fire.visible = false
        light.color.setHex(STROKE_COLORS.exhaust)
        light.intensity = 2.0 * (1 - rel)
        glow.material.color.setHex(STROKE_COLORS.exhaust)
        glow.scale.setScalar((4 + rel * 3.5) * EFFECT_SCALE)
        glow.material.opacity = 0.35 * (1 - rel)
      } else if (localPhase < 0.75) {
        strokeKey = 'intake'
        const rel = (localPhase - 0.5) / 0.25
        fire.visible = false
        const pulse = Math.sin(rel * Math.PI)
        light.color.setHex(STROKE_COLORS.intake)
        light.intensity = pulse * 1.6
        glow.material.color.setHex(STROKE_COLORS.intake)
        glow.scale.setScalar((3.5 + pulse * 0.8) * EFFECT_SCALE)
        glow.material.opacity = 0.3 * pulse
      } else {
        strokeKey = 'compression'
        const rel = (localPhase - 0.75) / 0.25
        fire.visible = false
        light.color.setHex(STROKE_COLORS.compression)
        light.intensity = rel * rel * 3.0
        glow.material.color.setHex(STROKE_COLORS.compression)
        glow.scale.setScalar((4.3 - rel * 1.0) * EFFECT_SCALE)
        glow.material.opacity = 0.15 + rel * rel * 0.35
      }

      strokeNamesCopy[cylIndex] = STROKE_NAMES[strokeKey]
    }

    function updateEngineShake(delta) {
      const model   = engineModelRef.current
      const basePos = engineBasePosRef.current
      if (!model || !basePos) return

      shakeClockRef.current += delta
      const vib = vibrationRef.current != null ? vibrationRef.current : 0.2
      const visualRPM = engineRPMRef.current

      const rotFreqHz = visualRPM / 60
      const idleAmp   = 0.015 + vib * 0.5
      const humX = Math.sin(shakeClockRef.current * rotFreqHz * Math.PI * 2) * idleAmp
      const humY = Math.sin(shakeClockRef.current * rotFreqHz * Math.PI * 2 * 1.7 + 1.3) * idleAmp * 0.6

      // Firing punch
      let punchX = 0, punchY = 0
      ;[0, 1].forEach((pairIndex) => {
        firingPunchRef.current[pairIndex] *= Math.max(0, 1 - delta * 14)
        const dir = pairIndex === 0 ? 1 : -1
        const amp = firingPunchRef.current[pairIndex] * (0.15 + vib * 0.6)
        punchX += dir * amp
        punchY += amp * 0.5
      })

      // Jitter
      jitterTimerRef.current += delta
      if (jitterTimerRef.current > JITTER_INTERVAL) {
        jitterTimerRef.current = 0
        const jitterAmp = 0.02 + vib * 0.25
        jitterTargetRef.current.set(
          (Math.random() - 0.5) * jitterAmp,
          (Math.random() - 0.5) * jitterAmp,
          (Math.random() - 0.5) * jitterAmp * 0.5
        )
      }
      jitterCurrentRef.current.lerp(jitterTargetRef.current, Math.min(1, delta * 10))

      model.position.set(
        basePos.x + humX + punchX + jitterCurrentRef.current.x,
        basePos.y + humY + punchY + jitterCurrentRef.current.y,
        basePos.z + jitterCurrentRef.current.z
      )
      model.rotation.z = humX * 0.02 + jitterCurrentRef.current.x * 0.01
      model.rotation.x = humY * 0.015 + jitterCurrentRef.current.y * 0.01
    }

    let lastStrokeUpdate = 0

    function animate() {
      animFrameRef.current = requestAnimationFrame(animate)

      const delta = clockRef.current.getDelta()

      // Map telemetry RPM to visual RPM
      engineRPMRef.current = mapRpmToVisual(rpmRef.current)

      const baseRotationSpeed = (engineRPMRef.current / 60) * Math.PI * 2 * delta

      if (mixerRef.current && mainActionRef.current) {
        mixerRef.current.timeScale = (engineRPMRef.current / 60) * nativeAnimDurRef.current
        mixerRef.current.update(delta)

        const progress      = mainActionRef.current.time / mainActionRef.current.getClip().duration
        const timingOffset  = 0.15
        const syncedProgress = (progress + timingOffset) % 1

        if (combustionLightsRef.current.length === 4) {
          for (let cyl = 0; cyl < 4; cyl++) {
            const localPhase = ((syncedProgress - cylinderFireTime[cyl]) % 1 + 1) % 1
            updateCylinderStroke(cyl, localPhase)
          }
        }

        // Update stroke names in React state (throttled to avoid perf hit)
        lastStrokeUpdate += delta
        if (lastStrokeUpdate > 0.1) {
          lastStrokeUpdate = 0
          setStrokeNames([...strokeNamesCopy])
        }
      }

      // Fluid pipe animation
      fluidMaterialsRef.current.forEach((item) => {
        item.mat.map.offset.x -= baseRotationSpeed * 0.1
      })

      // Mechanical parts rotation
      if (propGearRef.current)     propGearRef.current.rotation.y    += baseRotationSpeed / 2.43
      if (fuelPumpGearRef.current) fuelPumpGearRef.current.rotation.y -= baseRotationSpeed * 0.8
      if (alternatorRef.current)   alternatorRef.current.rotation.y   -= baseRotationSpeed * 1.5
      if (crankFrontRef.current)   crankFrontRef.current.rotation.y   -= baseRotationSpeed
      if (fuelImpellerRef.current) fuelImpellerRef.current.rotation.x += baseRotationSpeed * 1.2
      if (waterImpellerRef.current) waterImpellerRef.current.rotation.y -= baseRotationSpeed * 1.2

      // Engine shake
      updateEngineShake(delta)

      // Auto-rotate via controls
      if (controlsRef.current) {
        controlsRef.current.autoRotate = autoRotateRef.current
        controlsRef.current.update()
      }

      renderer.render(scene, camera)
    }

    animate()

    // ─────────────────────────────────────────────────────────
    // RESIZE HANDLER
    // ─────────────────────────────────────────────────────────
    const handleResize = () => {
      if (!container || !renderer || !camera) return
      const w = container.clientWidth
      const h = container.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }

    const resizeObserver = new ResizeObserver(handleResize)
    resizeObserver.observe(container)

    // ─────────────────────────────────────────────────────────
    // CLEANUP
    // ─────────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(animFrameRef.current)
      resizeObserver.disconnect()
      renderer.dispose()
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement)
      }
      // Reset refs
      combustionLightsRef.current = []
      particleSystemsRef.current  = []
      fireLayersRef.current        = []
      fireBrightnessRef.current    = []
      glowSpritesRef.current       = []
      fluidMaterialsRef.current    = []
    }
  }, []) // Only run once on mount

  // ─────────────────────────────────────────────────────────
  // AUTO-ROTATE REF (avoids stale closure in animate())
  // ─────────────────────────────────────────────────────────
  const autoRotateRef = useRef(autoRotate)
  useEffect(() => { autoRotateRef.current = autoRotate }, [autoRotate])

  // ─────────────────────────────────────────────────────────
  // RESET CAMERA
  // ─────────────────────────────────────────────────────────
  const handleResetCamera = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return
    cameraRef.current.position.set(40, 20, 50)
    cameraRef.current.lookAt(0, 0, 0)
    controlsRef.current.reset()
  }, [])

  // ─────────────────────────────────────────────────────────
  // STATUS BAR LABEL
  // ─────────────────────────────────────────────────────────
  const healthColor = {
    HEALTHY:   '#22c55e',
    WARNING:   '#f59e0b',
    DEGRADING: '#f97316',
    CRITICAL:  '#ef4444',
  }[healthStatus] || '#8FA8BC'

  return (
    <div className={`relative w-full h-full bg-bg-base overflow-hidden ${className}`}>
      {/* Three.js container */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* Loading overlay */}
      {!isLoaded && !loadError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-bg-base/90 z-10">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
          <p className="font-mono text-xs text-text-muted uppercase tracking-widest">Loading 3D Engine Model</p>
          <p className="font-mono text-xs text-text-muted/50 mt-1">Rotax 912-style · GLB</p>
        </div>
      )}

      {/* Error overlay */}
      {loadError && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-bg-base/95 z-10 p-4">
          <div className="text-status-critical text-xs font-mono mb-2 uppercase tracking-wider">⚠ Model Load Failed</div>
          <p className="text-text-muted text-xs font-mono text-center">{loadError}</p>
          <p className="text-text-muted/50 text-xs font-mono mt-2">Check that the backend server is running at {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}</p>
        </div>
      )}

      {/* Health status indicator overlay (top-left) */}
      {isLoaded && healthStatus && (
        <div className="absolute top-3 left-3 z-20 flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ backgroundColor: healthColor, boxShadow: `0 0 6px ${healthColor}` }}
          />
          <span className="font-mono text-xs uppercase tracking-widest" style={{ color: healthColor }}>
            {healthStatus}
          </span>
        </div>
      )}

      {/* Cylinder stroke HUD (bottom-left) */}
      {isLoaded && (
        <div className="absolute bottom-12 left-3 z-20 bg-bg-panel/80 border border-bg-border rounded-sm px-2 py-1.5 backdrop-blur-sm">
          <div className="text-[10px] font-mono text-text-muted mb-1 uppercase tracking-widest">Cylinders</div>
          {strokeNames.map((name, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[10px] font-mono">
              <span className="text-text-muted w-8">Cyl {i + 1}</span>
              <span className={
                name === 'Power'       ? 'text-white' :
                name === 'Exhaust'     ? 'text-gray-400' :
                name === 'Intake'      ? 'text-blue-400' :
                name === 'Compression' ? 'text-amber-400' : 'text-text-muted'
              }>{name}</span>
            </div>
          ))}
        </div>
      )}

      {/* Toolbar (bottom right) */}
      {isLoaded && (
        <div className="absolute bottom-3 right-3 z-20 flex gap-2">
          <button
            onClick={() => setAutoRotate((v) => !v)}
            className={`p-1.5 border font-mono text-xs uppercase transition-all ${
              autoRotate ? 'border-primary text-primary bg-primary/10' : 'border-bg-border text-text-muted hover:border-primary hover:text-primary'
            }`}
            title={autoRotate ? 'Stop auto-rotate' : 'Auto-rotate'}
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetCamera}
            className="p-1.5 border border-bg-border text-text-muted hover:border-primary hover:text-primary transition-all"
            title="Reset camera"
          >
            <Eye className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Fault type indicator (top-right) */}
      {isLoaded && faultType && faultType !== 'NORMAL' && faultType !== 'NONE' && (
        <div className="absolute top-3 right-3 z-20">
          <div className="bg-status-critical/20 border border-status-critical text-status-critical font-mono text-[10px] uppercase tracking-wider px-2 py-1">
            ⚠ {faultType.replace(/_/g, ' ')}
          </div>
        </div>
      )}
    </div>
  )
}
