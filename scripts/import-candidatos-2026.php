<?php
/**
 * Importação pontual dos candidatos 2026 (com fotos) pra pressao_candidatos.
 *
 * Uso (via wp-cli, dentro de um pod com o wp-content do tarifazero) —
 * eval-file só aceita argumentos POSICIONAIS (sem --key=value):
 *   wp eval-file import-candidatos-2026.php /tmp/import/candidatos.csv /tmp/import/icon dry-run 10
 *   wp eval-file import-candidatos-2026.php /tmp/import/candidatos.csv /tmp/import/icon run 10
 *   wp eval-file import-candidatos-2026.php /tmp/import/candidatos.csv /tmp/import/icon run 0
 *
 * Args posicionais: <csv> <icons_dir> <dry-run|run> [<limit, 0 = sem limite>]
 *
 * Reaproveita PressaoPlugin_Admin::sanitize_one_candidato() (mesmo validador
 * usado pelo CRUD via AJAX) pra garantir formato idêntico ao que a busca e a
 * tabela de admin já esperam. Idempotente por SQ_CANDIDATO (campo extra
 * "sq_candidato" gravado em cada linha, usado só por este script).
 */

if (!class_exists('PressaoPlugin_Admin')) {
    WP_CLI::error('PressaoPlugin_Admin não carregada — o plugin pressao-plugin precisa estar ativo.');
}

/**
 * Confirma que um attachment foi offloadado pro S3 (linha em wp_as3cf_items)
 * e, se não foi, dispara o handler de upload diretamente. Achado durante o
 * piloto: media_handle_sideload() só offloada automaticamente se
 * is_plugin_setup() já estava true NO MOMENTO da chamada — se o plugin não
 * estiver totalmente pronto por qualquer razão nesse instante, o hook
 * silenciosamente não faz nada (sem erro visível). Essa função funciona como
 * uma segunda tentativa explícita, sempre.
 */
function as3cf_ensure_offloaded($attachment_id, $row_num, $sq, &$errors) {
    global $wpdb;

    $exists = $wpdb->get_var($wpdb->prepare(
        "SELECT id FROM {$wpdb->prefix}as3cf_items WHERE source_id = %d AND source_type = 'media-library'",
        $attachment_id
    ));
    if ($exists) {
        return true;
    }

    if (!class_exists('DeliciousBrains\\WP_Offload_Media\\Items\\Media_Library_Item')) {
        // Versão diferente do plugin (ex.: Lite) — sem esse mecanismo,
        // segue sem tentar de novo; wp_update_attachment_metadata já foi
        // a única via disponível.
        return false;
    }

    global $as3cf;
    if (!$as3cf) {
        $errors[] = "Linha $row_num (SQ=$sq): \$as3cf global ausente, não foi possível confirmar offload.";
        return false;
    }

    $item = DeliciousBrains\WP_Offload_Media\Items\Media_Library_Item::create_from_source_id($attachment_id);
    if (is_wp_error($item)) {
        $errors[] = "Linha $row_num (SQ=$sq): offload — " . $item->get_error_message();
        return false;
    }

    $handler = $as3cf->get_item_handler('upload');
    $result = $handler->handle($item, ['offloaded_files' => []]);
    if (is_wp_error($result)) {
        $errors[] = "Linha $row_num (SQ=$sq): offload — " . $result->get_error_message();
        return false;
    }

    return true;
}

$csv_path = $args[0] ?? '';
$icons_dir = isset($args[1]) ? rtrim($args[1], '/') : '';
$mode = $args[2] ?? 'dry-run';
$dry_run = ($mode !== 'run');
$limit = isset($args[3]) ? (int) $args[3] : 0;
$batch_size = 100;

if (!$csv_path || !file_exists($csv_path)) {
    WP_CLI::error('CSV não encontrado: ' . $csv_path);
}
if (!$icons_dir || !is_dir($icons_dir)) {
    WP_CLI::error('Pasta de fotos não encontrada: ' . $icons_dir);
}

// Handles que não são perfis reais (termos reservados do Instagram usados
// como valor default quando o candidato não preencheu o @ de verdade) —
// ver achado na planilha 2026 (4x @invites, 3x @channel).
$junk_handles = ['invites', 'channel'];

$fh = fopen($csv_path, 'rb');
if (!$fh) {
    WP_CLI::error('Não foi possível abrir o CSV.');
}

$first_line = fgets($fh);
if ($first_line === false) {
    WP_CLI::error('CSV vazio.');
}
if (strncmp($first_line, "\xEF\xBB\xBF", 3) === 0) {
    $first_line = substr($first_line, 3);
}
$delimiter = (substr_count($first_line, ';') > substr_count($first_line, ',')) ? ';' : ',';
$headers = str_getcsv(trim($first_line), $delimiter);
$col = array_flip($headers);

$required = ['SQ_CANDIDATO', 'NM_URNA_CANDIDATO', 'DS_CARGO', 'SG_PARTIDO', 'INSTAGRAM', 'FOTO'];
foreach ($required as $r) {
    if (!isset($col[$r])) {
        WP_CLI::error("Coluna obrigatória ausente no CSV: $r");
    }
}

$existing = get_option('pressao_candidatos', []);
if (!is_array($existing)) {
    $existing = [];
}
$existing_sq = [];
foreach ($existing as $item) {
    if (!empty($item['sq_candidato'])) {
        $existing_sq[(string) $item['sq_candidato']] = true;
    }
}

$stats = [
    'total_rows' => 0,
    'skipped_junk' => 0,
    'skipped_existing' => 0,
    'skipped_no_photo' => 0,
    'skipped_invalid' => 0,
    'processed' => 0,
];
$errors = [];
$batch = [];
$row_num = 1;

$flush_batch = function () use (&$batch, &$existing, $dry_run) {
    if (empty($batch)) {
        return;
    }
    if (!$dry_run) {
        $existing = array_merge($existing, $batch);
        update_option('pressao_candidatos', $existing, false);
    }
    WP_CLI::log(($dry_run ? '[dry-run] ' : '') . 'lote de ' . count($batch) . ' — total acumulado: ' . count($existing));
    $batch = [];
};

while (($row = fgetcsv($fh, 0, $delimiter)) !== false) {
    $row_num++;

    if (count($row) < count($headers)) {
        continue;
    }
    $stats['total_rows']++;

    if ($limit > 0 && $stats['processed'] >= $limit) {
        break;
    }

    $sq = trim($row[$col['SQ_CANDIDATO']]);
    $instagram_raw = trim($row[$col['INSTAGRAM']]);
    $handle_lower = strtolower(ltrim($instagram_raw, '@'));

    if (in_array($handle_lower, $junk_handles, true)) {
        $stats['skipped_junk']++;
        WP_CLI::log("Linha $row_num pulada (handle placeholder): SQ_CANDIDATO=$sq @$handle_lower");
        continue;
    }

    if (isset($existing_sq[$sq])) {
        $stats['skipped_existing']++;
        continue;
    }

    $foto_filename = basename(trim($row[$col['FOTO']]));
    $foto_path = $icons_dir . '/' . $foto_filename;

    if (!file_exists($foto_path)) {
        $stats['skipped_no_photo']++;
        $errors[] = "Linha $row_num (SQ=$sq): foto não encontrada ($foto_path)";
        continue;
    }

    $raw_candidato = [
        'nome' => $row[$col['NM_URNA_CANDIDATO']],
        'cargo' => $row[$col['DS_CARGO']],
        'partido' => $row[$col['SG_PARTIDO']],
        'descricao' => '',
        'link_url' => $instagram_raw,
        'imagem_id' => 0,
    ];

    $sanitized = PressaoPlugin_Admin::sanitize_one_candidato($raw_candidato);
    if ($sanitized === null) {
        $stats['skipped_invalid']++;
        $errors[] = "Linha $row_num (SQ=$sq): dados insuficientes após sanitização";
        continue;
    }

    $imagem_id = 0;
    if (!$dry_run) {
        if (!function_exists('media_handle_sideload')) {
            require_once ABSPATH . 'wp-admin/includes/image.php';
            require_once ABSPATH . 'wp-admin/includes/file.php';
            require_once ABSPATH . 'wp-admin/includes/media.php';
        }

        // Copia pra um tmp separado — media_handle_sideload() pode mover o
        // arquivo original, e queremos preservar a pasta de fotos intacta.
        $tmp_copy = wp_tempnam($foto_filename);
        if (!copy($foto_path, $tmp_copy)) {
            $stats['skipped_no_photo']++;
            $errors[] = "Linha $row_num (SQ=$sq): falha ao copiar foto pra tmp";
            continue;
        }

        $file_array = [
            'name' => $foto_filename,
            'tmp_name' => $tmp_copy,
        ];
        $attachment_id = media_handle_sideload($file_array, 0, $sanitized['nome']);

        if (is_wp_error($attachment_id)) {
            $errors[] = "Linha $row_num (SQ=$sq): erro no upload — " . $attachment_id->get_error_message();
            @unlink($tmp_copy);
            continue;
        }
        $imagem_id = (int) $attachment_id;

        // media_handle_sideload() já dispara wp_update_attachment_metadata,
        // que o AS3CF escuta pra fazer o offload — mas isso só funciona se
        // o plugin já se considerar "configurado" (bucket/credenciais) no
        // momento exato da chamada. Confirma aqui, de forma explícita, e
        // dispara de novo se não tiver ido pro S3 — não confia só no
        // encadeamento implícito de hooks.
        if (function_exists('as3cf_ensure_offloaded')) {
            as3cf_ensure_offloaded($imagem_id, $row_num, $sq, $errors);
        }
    }

    $sanitized['imagem_id'] = $imagem_id;
    // URL já resolvida (pós-offload) e guardada na linha — evita que a
    // busca/autocomplete precise chamar wp_get_attachment_image_url() por
    // resultado (ver otimização de performance em class-shortcode.php).
    $sanitized['imagem'] = $imagem_id ? (wp_get_attachment_image_url($imagem_id, 'thumbnail') ?: '') : '';
    $sanitized['uid'] = substr(wp_generate_password(20, false, false), 0, 12);
    $sanitized['sq_candidato'] = $sq;

    $batch[] = $sanitized;
    $existing_sq[$sq] = true;
    $stats['processed']++;

    if (count($batch) >= $batch_size) {
        $flush_batch();
    }
}

$flush_batch();
fclose($fh);

WP_CLI::log('');
WP_CLI::log('--- Resumo' . ($dry_run ? ' (dry-run, nada foi gravado)' : '') . ' ---');
WP_CLI::log('Linhas lidas: ' . $stats['total_rows']);
WP_CLI::log('Processados: ' . $stats['processed']);
WP_CLI::log('Pulados (handle placeholder): ' . $stats['skipped_junk']);
WP_CLI::log('Pulados (já existia — mesmo SQ_CANDIDATO): ' . $stats['skipped_existing']);
WP_CLI::log('Pulados (sem foto): ' . $stats['skipped_no_photo']);
WP_CLI::log('Pulados (inválido após sanitização): ' . $stats['skipped_invalid']);
WP_CLI::log('Total em pressao_candidatos agora: ' . count($existing));

if (!empty($errors)) {
    WP_CLI::log('');
    WP_CLI::log('Erros (' . count($errors) . ' no total, mostrando até 20):');
    foreach (array_slice($errors, 0, 20) as $e) {
        WP_CLI::log('  - ' . $e);
    }
}
