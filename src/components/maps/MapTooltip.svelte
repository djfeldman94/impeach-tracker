<script lang="ts">
  import { STANCE_COLORS, STANCE_LABELS, getPartyLabel, getPartyColor, type MemberData } from './map-utils';

  interface Props {
    member: MemberData | null;
    x: number;
    y: number;
    visible: boolean;
    /** If multiple members (e.g. 2 senators), show them all */
    members?: MemberData[];
  }

  let { member = null, x = 0, y = 0, visible = false, members = [] }: Props = $props();

  const displayMembers = $derived(members.length > 0 ? members : member ? [member] : []);

  let tooltipEl: HTMLDivElement;

  const style = $derived.by(() => {
    if (!visible) return 'display: none';
    // Offset from cursor
    const offsetX = 12;
    const offsetY = 12;
    return `left: ${x + offsetX}px; top: ${y + offsetY}px`;
  });
</script>

<div class="tooltip" bind:this={tooltipEl} style={style} role="tooltip">
  {#each displayMembers as m}
    <div class="tooltip-member">
      <div class="tooltip-name">
        <span class="tooltip-party-dot" style="background: {getPartyColor(m.party)}"></span>
        {m.fullName}
        <span class="tooltip-party">({m.party})</span>
      </div>
      <div class="tooltip-location">
        {m.state}{m.district != null ? `-${m.district}` : ''}
      </div>
      <div class="tooltip-stance">
        <span class="tooltip-stance-dot" style="background: {STANCE_COLORS[m.stance]}"></span>
        {STANCE_LABELS[m.stance]}
      </div>
    </div>
  {/each}
  {#if displayMembers.length === 0}
    <div class="tooltip-empty">No data available</div>
  {/if}
</div>

<style>
  .tooltip {
    position: fixed;
    z-index: 1000;
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 12px;
    pointer-events: none;
    font-size: 0.8rem;
    line-height: 1.5;
    max-width: 280px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }

  .tooltip-member + .tooltip-member {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px solid #30363d;
  }

  .tooltip-name {
    font-weight: 600;
    color: #e6edf3;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .tooltip-party {
    color: #8b949e;
    font-weight: 400;
  }

  .tooltip-party-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .tooltip-location {
    color: #8b949e;
    font-size: 0.75rem;
  }

  .tooltip-stance {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 2px;
  }

  .tooltip-stance-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .tooltip-empty {
    color: #6e7681;
  }
</style>
