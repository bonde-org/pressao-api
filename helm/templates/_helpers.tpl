{{/*
Expand the name of the chart.
*/}}
{{- define "pressao-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "pressao-api.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label.
*/}}
{{- define "pressao-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "pressao-api.labels" -}}
helm.sh/chart: {{ include "pressao-api.chart" . }}
{{ include "pressao-api.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "pressao-api.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pressao-api.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
ServiceAccount name.
*/}}
{{- define "pressao-api.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "pressao-api.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Application secret name (non-database credentials).
*/}}
{{- define "pressao-api.secretName" -}}
{{- if .Values.secrets.existingSecret }}
{{- .Values.secrets.existingSecret }}
{{- else }}
{{- printf "%s-app" (include "pressao-api.fullname" .) }}
{{- end }}
{{- end }}

{{/*
CNPG cluster name.
*/}}
{{- define "pressao-api.cnpg.clusterName" -}}
{{- default (printf "%s-pg" (include "pressao-api.fullname" .)) .Values.database.clusterName }}
{{- end }}

{{/*
CNPG superuser secret name.
*/}}
{{- define "pressao-api.cnpg.superuserSecretName" -}}
{{- default (printf "%s-superuser" (include "pressao-api.cnpg.clusterName" .)) .Values.database.superuser.secretName }}
{{- end }}

{{/*
Secret that provides DATABASE_URL.
When CNPG is enabled, CloudNativePG cria {cluster}-app com a chave `uri`.
*/}}
{{- define "pressao-api.databaseSecretName" -}}
{{- if .Values.database.enabled }}
{{- printf "%s-app" (include "pressao-api.cnpg.clusterName" .) }}
{{- else if .Values.database.existingSecret }}
{{- .Values.database.existingSecret }}
{{- else }}
{{- include "pressao-api.secretName" . }}
{{- end }}
{{- end }}

{{- define "pressao-api.databaseSecretKey" -}}
{{- if .Values.database.enabled }}
{{- default "uri" .Values.database.cnpgUriKey }}
{{- else }}
{{- default "DATABASE_URL" .Values.database.urlKey }}
{{- end }}
{{- end }}
