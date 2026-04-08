<script lang="ts">
  import { onMount } from 'svelte';
  import { geoPath, geoAlbersUsa } from 'd3-geo';
  import { zoom, zoomIdentity, type ZoomBehavior } from 'd3-zoom';
  import { select } from 'd3-selection';
  import * as topojson from 'topojson-client';
  import { getStanceColor, buildFipsLookup, type MemberData } from './map-utils';
  import MapTooltip from './MapTooltip.svelte';
  import MapLegend from './MapLegend.svelte';

  interface Props {
    members: MemberData[];
    compact?: boolean;
  }

  let { members, compact = false }: Props = $props();

  let containerEl: HTMLDivElement;
  let svgEl: SVGSVGElement;
  let width = $state(960);
  let height = $state(600);
  let features: any[] = $state([]);
  let pathStrings: Map<string, string> = $state(new Map());
  let loading = $state(true);

  // Zoom state
  let currentTransform = $state('');
  let currentScale = $state(1);
  let zoomBehavior: ZoomBehavior<SVGSVGElement, unknown>;

  // Tooltip state
  let tooltipVisible = $state(false);
  let tooltipX = $state(0);
  let tooltipY = $state(0);
  let tooltipMember = $state<MemberData | null>(null);
  let hoveredGeoid = $state<string | null>(null);

  const fipsLookup = $derived(buildFipsLookup(members));

  // Adjust stroke width inversely to zoom so borders don't get thick
  const strokeWidth = $derived(0.3 / currentScale);
  const hoverStrokeWidth = $derived(1.5 / currentScale);

  function computePaths(w: number, h: number, feats: any[]) {
    const projection = geoAlbersUsa().scale(w * 1.2).translate([w / 2, h / 2]);
    const pathGen = geoPath(projection);
    const map = new Map<string, string>();
    for (const f of feats) {
      const d = pathGen(f);
      if (d) {
        map.set(f.properties.GEOID, d);
      }
    }
    return map;
  }

  function setupZoom() {
    if (!svgEl) return;

    const svgSelection = select(svgEl);

    zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 12])
      .on('zoom', (event) => {
        const { x, y, k } = event.transform;
        currentTransform = `translate(${x},${y}) scale(${k})`;
        currentScale = k;

        // Hide tooltip while zooming/panning
        if (event.sourceEvent) {
          tooltipVisible = false;
        }
      });

    svgSelection.call(zoomBehavior);

    // Prevent default scroll when over the map
    svgSelection.on('wheel.zoom', function(event) {
      event.preventDefault();
      // Re-dispatch to d3-zoom
      zoomBehavior.call(this as any, svgSelection as any);
    }, { passive: false });
  }

  function resetZoom() {
    if (!svgEl || !zoomBehavior) return;
    const svgSelection = select(svgEl);
    svgSelection.transition().duration(300).call(zoomBehavior.transform, zoomIdentity);
  }

  onMount(async () => {
    if (containerEl) {
      const rect = containerEl.getBoundingClientRect();
      width = rect.width;
      height = compact ? rect.width * 0.55 : rect.width * 0.625;
    }

    const res = await fetch('/geo/us-congress-districts.topo.json');
    const topo = await res.json();
    const layerName = Object.keys(topo.objects)[0];
    features = topojson.feature(topo, topo.objects[layerName]).features;
    pathStrings = computePaths(width, height, features);
    loading = false;

    // Set up zoom after a tick so SVG is in the DOM
    requestAnimationFrame(() => setupZoom());

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (Math.abs(w - width) > 10) {
          width = w;
          height = compact ? w * 0.55 : w * 0.625;
          pathStrings = computePaths(width, height, features);
          // Reset zoom on resize
          if (zoomBehavior && svgEl) {
            const svgSelection = select(svgEl);
            svgSelection.call(zoomBehavior.transform, zoomIdentity);
          }
        }
      }
    });
    observer.observe(containerEl);

    return () => observer.disconnect();
  });

  function getFillColor(geoid: string): string {
    const memberList = fipsLookup.get(geoid);
    if (memberList && memberList.length > 0) {
      return getStanceColor(memberList[0].stance);
    }
    return '#2d333b';
  }

  function handleMouseMove(e: MouseEvent, geoid: string) {
    const memberList = fipsLookup.get(geoid);
    if (memberList && memberList.length > 0) {
      tooltipMember = memberList[0];
      tooltipVisible = true;
      tooltipX = e.clientX;
      tooltipY = e.clientY;
      hoveredGeoid = geoid;
    }
  }

  function handleMouseLeave() {
    tooltipVisible = false;
    tooltipMember = null;
    hoveredGeoid = null;
  }

  function handleClick(geoid: string) {
    const memberList = fipsLookup.get(geoid);
    if (memberList && memberList.length > 0) {
      window.location.href = `/house/${memberList[0].slug}`;
    }
  }

  function handleKeyDown(e: KeyboardEvent, geoid: string) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick(geoid);
    }
  }
</script>

<div class="house-map" bind:this={containerEl}>
  {#if loading}
    <div class="map-loading" style="height: {height}px">
      <span>Loading district map...</span>
    </div>
  {:else}
    <div class="map-controls">
      <button class="zoom-btn" onclick={() => {
        if (!svgEl || !zoomBehavior) return;
        select(svgEl).transition().duration(200).call(zoomBehavior.scaleBy, 1.5);
      }} aria-label="Zoom in">+</button>
      <button class="zoom-btn" onclick={() => {
        if (!svgEl || !zoomBehavior) return;
        select(svgEl).transition().duration(200).call(zoomBehavior.scaleBy, 0.67);
      }} aria-label="Zoom out">&minus;</button>
      {#if currentScale > 1.05}
        <button class="zoom-btn zoom-btn--reset" onclick={resetZoom} aria-label="Reset zoom">Reset</button>
      {/if}
    </div>

    <svg
      bind:this={svgEl}
      viewBox="0 0 {width} {height}"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Map of US congressional districts colored by impeachment stance. Scroll to zoom, drag to pan."
    >
      <g transform={currentTransform}>
        {#each features as feature (feature.properties.GEOID)}
          {@const geoid = feature.properties.GEOID}
          {@const d = pathStrings.get(geoid)}
          {#if d}
            <path
              {d}
              fill={getFillColor(geoid)}
              stroke="#0d1117"
              stroke-width={hoveredGeoid === geoid ? hoverStrokeWidth : strokeWidth}
              opacity={hoveredGeoid && hoveredGeoid !== geoid ? 0.6 : 1}
              class="district-path"
              role="button"
              tabindex="0"
              aria-label={fipsLookup.get(geoid)?.[0]?.fullName || feature.properties.NAME}
              onmousemove={(e) => handleMouseMove(e, geoid)}
              onmouseleave={handleMouseLeave}
              onclick={() => handleClick(geoid)}
              onkeydown={(e) => handleKeyDown(e, geoid)}
            />
          {/if}
        {/each}
      </g>
    </svg>
    <MapLegend />
  {/if}

  <MapTooltip
    member={tooltipMember}
    x={tooltipX}
    y={tooltipY}
    visible={tooltipVisible}
  />
</div>

<style>
  .house-map {
    width: 100%;
    position: relative;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
    cursor: grab;
  }

  svg:active {
    cursor: grabbing;
  }

  .district-path {
    cursor: pointer;
    transition: opacity 0.15s;
    will-change: fill, opacity;
  }

  .district-path:focus-visible {
    outline: 2px solid #58a6ff;
    outline-offset: -2px;
  }

  .map-controls {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    z-index: 10;
  }

  .zoom-btn {
    width: 32px;
    height: 32px;
    border: 1px solid #30363d;
    background: #161b22;
    color: #e6edf3;
    font-size: 1.1rem;
    font-family: inherit;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
    line-height: 1;
  }

  .zoom-btn:hover {
    background: #30363d;
  }

  .zoom-btn--reset {
    width: auto;
    padding: 0 8px;
    font-size: 0.7rem;
    margin-top: 2px;
  }

  .map-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    background: #161b22;
    border-radius: 4px;
    color: #6e7681;
    font-size: 0.9rem;
  }
</style>
