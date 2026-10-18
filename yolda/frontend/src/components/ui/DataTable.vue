<template><div class="scroll-x"><table class="t"><slot /></table></div></template>
<style>
.t{width:100%;border-collapse:collapse;font-size:13px}
.t th{font-size:12px;font-weight:600;color:var(--muted);padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
.t td{white-space:nowrap;padding:10px 12px;border-bottom:1px solid var(--line-2);vertical-align:middle}
.t tbody tr.click{cursor:pointer}.t tbody tr.click:hover{background:var(--surface-2)}
.t td.wrap{white-space:normal;min-width:200px}.t .r{text-align:right}.t tfoot td{font-weight:700;border-bottom:0}
.t tr.flash td{background:var(--brand-soft)}
.t th.sortable{cursor:pointer;user-select:none}
.t .s{font-size:12px;color:var(--muted)}
</style>
