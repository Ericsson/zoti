// Template: ShiftFarm.C
{% set iterate_over = param.iterate_over|setdefaults({"offset": "0", "range": "type.size" }) %}

{% macro itrange() -%}
{% set ranges = [] %}
{% for k,p in iterate_over.items() -%}
{% do ranges.append(port[k]|find(p.range)) %}
{%- endfor %}min({{ ranges|join(", ") }})
{%- endmacro %}

for ({{ port._it.name }} = 0; {{ port._it.name }} < {{ itrange() }} ; {{ port._it.name }}++){
  {{ port._range.name }} = {{ itrange() }} - {{ port._it.name }};
  {{ placeholder["f"] }}
}
// End: ShiftFarm.C


// Template: FarmRed_Acc.C
{% set iterate_over = param.iterate_over|setdefaults({"offset": "0", "range": "type.size" }) %}

{% macro itrange() -%}
{% set ranges = [] %}
{% for k,p in iterate_over.items() -%}
{% do ranges.append(port[k]|find(p.range)) %}
{%- endfor %}min({{ ranges|join(", ") }})
{%- endmacro %}

for ({{ port._it.name }} = 0; {{ port._it.name }} < {{ itrange() }} ; {{ port._it.name }}++){
  {{ placeholder["f"] }}
}
{{ port.out1.name }} = {{ port._acc.name }};
// End: FarmRed_Acc.C

