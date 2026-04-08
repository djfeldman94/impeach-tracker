<script lang="ts">
  import { onMount } from 'svelte';
  import { geoPath, geoAlbersUsa } from 'd3-geo';
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
  let width = $state(960);
  let height = $state(600);
  let features: any[] = $state([]);
  let pathStrings: Map<string, string> = $state(new Map());
  let loading = $state(true);

  // Tooltip state
  let tooltipVisible = $state(false);
  let tooltipX = $state(0);
  let tooltipY = $state(0);
  let tooltipMember = $state<MemberData | null>(null);
  let hoveredGeoid = $state<string | null>(null);

  const fipsLookup = $derived(buildFipsLookup(members));

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

  onMount(async () => {
    if (containerEl) {
      const rect = containerEl.getBoundingClientRect();
      width = rect.width;
      height = compact ? rect.width * 0.55 : rect.width * 0.625;
    }

    const res = await fetch('/geo/us-states.topo.json');
    const topo = await res.json();
    const layerName = Object.keys(topo.objects)[0];
    features = topojson.feature(topo, topo.objects[layerName]).features;
    pathStrings = computePaths(width, height, features);
    loading = false;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (Math.abs(w - width) > 10) {
          width = w;
          height = compact ? w * 0.55 : w * 0.625;
          pathStrings = computePaths(width, height, features);
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
      window.location.href = `/governors/${memberList[0].slug}`;
    }
  }

  function handleKeyDown(e: KeyboardEvent, geoid: string) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick(geoid);
    }
  }
</script>

<div class="governor-map" bind:this={containerEl}>
  {#if loading}
    <div class="map-loading" style="height: {height}px">
      <span>Loading governor map...</span>
    </div>
  {:else}
    <svg
      viewBox="0 0 {width} {height}"
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label="Map of US states colored by governor impeachment stance"
    >
      {#each features as feature (feature.properties.GEOID)}
        {@const geoid = feature.properties.GEOID}
        {@const d = pathStrings.get(geoid)}
        {#if d}
          <path
            {d}
            fill={getFillColor(geoid)}
            stroke="#0d1117"
            stroke-width={hoveredGeoid === geoid ? 1.5 : 0.5}
            opacity={hoveredGeoid && hoveredGeoid !== geoid ? 0.6 : 1}
            class="state-path"
            role="button"
            tabindex="0"
            aria-label={feature.properties.NAME || feature.properties.STUSPS}
            onmousemove={(e) => handleMouseMove(e, geoid)}
            onmouseleave={handleMouseLeave}
            onclick={() => handleClick(geoid)}
            onkeydown={(e) => handleKeyDown(e, geoid)}
          />
        {/if}
      {/each}
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
  .governor-map {
    width: 100%;
    position: relative;
  }

  svg {
    width: 100%;
    height: auto;
    display: block;
  }

  .state-path {
    cursor: pointer;
    transition: opacity 0.15s;
    will-change: fill, opacity;
  }

  .state-path:focus-visible {
    outline: 2px solid #58a6ff;
    outline-offset: -2px;
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
