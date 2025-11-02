import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# NeurIPS style configuration
NEURIPS_STYLE = {
    'figure.figsize': (6, 4),
    'figure.dpi': 300,
    'font.size': 10,
    'font.family': 'serif',
    'font.serif': ['Times', 'Computer Modern Roman', 'DejaVu Serif'],
    'axes.labelsize': 10,
    'axes.titlesize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 9,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'lines.linewidth': 1.5,
    'patch.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
}

# Apply style
plt.rcParams.update(NEURIPS_STYLE)

# Sample data (replace with your actual data)
data = {
    'types': ['click', 'fill', 'navigate', 'scroll', 'wait'],
    'success_rates': [89.5, 76.2, 82.3, 67.8, 91.4],
    'total': [237, 145, 98, 78, 42]
}

COLORS = {'primary': '#2E86AB'}

fig, ax = plt.subplots(figsize=(7, 5))

x = np.arange(len(data['types']))
width = 0.6

# Create bars
bars = ax.bar(x, data['success_rates'], width,
             color=COLORS['primary'], alpha=0.8, edgecolor='black', linewidth=0.5)

# Add value labels on bars
for i, (bar, rate) in enumerate(zip(bars, data['success_rates'])):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 1,
           f'{rate:.1f}%',
           ha='center', va='bottom', fontsize=9)

# Customize axes
ax.set_xlabel('Action Type', fontweight='bold')
ax.set_ylabel('Success Rate (%)', fontweight='bold')
ax.set_title('Action Success Rates by Type', fontweight='bold', pad=15)
ax.set_xticks(x)
ax.set_xticklabels(data['types'], rotation=0)
ax.set_ylim(-15, 110)
ax.grid(axis='y', alpha=0.3, linestyle='--')

# Add total count annotations with better spacing
for i, (type_name, total) in enumerate(zip(data['types'], data['total'])):
    ax.text(i, -10, f'n={total}', ha='center', va='top', fontsize=8, style='italic')

plt.tight_layout()
fig.savefig('action_distribution_improved.png', format='png', bbox_inches='tight', dpi=300)
fig.savefig('action_distribution_improved.pdf', format='pdf', bbox_inches='tight', dpi=300)
print("✓ Saved action_distribution_improved.png and action_distribution_improved.pdf")
plt.close(fig)