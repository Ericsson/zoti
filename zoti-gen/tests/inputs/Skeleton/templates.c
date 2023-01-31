// Template: ShiftFarm.C
{# set iterate_over = param.iterate_over|setdefaults({"offset": "0", "range": "type.size" }) #}
{% set iterate_over = param.iterate_over|setdefaults({"offset": "0", "range": "name" }) %}

{% macro itrange() -%}
{% set ranges = [] %}
{% for k,p in iterate_over.items() -%}
{% do ranges.append(label[k]|find(p.range)) %}
{%- endfor %}min({{ ranges|join(", ") }})
{%- endmacro %}

for ({{ label._it.name }} = 0; {{ label._it.name }} < {{ itrange() }} ; {{ label._it.name }}++){
  {{ label._range.name }} = {{ itrange() }} - {{ label._it.name }};
  {{ placeholder["f"] }}
}
// End: ShiftFarm.C


// Template: FarmRed_Acc.C
{% set iterate_over = param.iterate_over|setdefaults({"offset": "0", "range": "name" }) %}

{% macro itrange() -%}
{% set ranges = [] %}
{% for k,p in iterate_over.items() -%}
{% do ranges.append(label[k]|find(p.range)) %}
{%- endfor %}min({{ ranges|join(", ") }})
{%- endmacro %}

for ({{ label._it.name }} = 0; {{ label._it.name }} < {{ itrange() }} ; {{ label._it.name }}++){
  {{ placeholder["f"] }}
}
{{ label.out1.name }} = {{ label._acc.name }};
// End: FarmRed_Acc.C

