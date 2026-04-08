<script lang="ts">
  import { STANCE_COLORS, STANCE_LABELS } from './map-utils';
  import type { StanceCategory } from '../../styles/colors';

  const categories: StanceCategory[] = [
    'cosponsor',
    'publicly-supports',
    'leaning-support',
    'silent',
    'leaning-oppose',
    'publicly-opposes',
  ];
</script>

<div class="legend" role="list" aria-label="Stance color legend">
  {#each categories as cat}
    <div class="legend-item" role="listitem">
      <span class="legend-dot" style="background: {STANCE_COLORS[cat]}"></span>
      <span class="legend-label">{STANCE_LABELS[cat]}</span>
    </div>
  {/each}
</div>

<style>
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    padding: 8px 0;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .legend-label {
    font-size: 0.75rem;
    color: #8b949e;
  }
</style>
