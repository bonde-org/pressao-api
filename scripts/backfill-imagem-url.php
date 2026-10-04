<?php
/**
 * Backfill único: resolve e grava a URL da imagem (campo "imagem") em cada
 * linha de pressao_candidatos que já tem imagem_id mas ainda não tem essa
 * URL guardada — necessário depois de otimizar a busca pra ler a URL
 * pronta em vez de recalcular com wp_get_attachment_image_url() a cada
 * request (ver sanitize_one_candidato() / normalize_candidatos_for_fluxo()).
 *
 * Uso: wp eval-file backfill-imagem-url.php
 */

$list = get_option('pressao_candidatos', []);
if (!is_array($list)) {
    WP_CLI::error('pressao_candidatos não é um array.');
}

$total = count($list);
$updated = 0;
$already_ok = 0;
$sem_imagem = 0;

foreach ($list as $index => $item) {
    if (!is_array($item)) {
        continue;
    }
    $imagem_id = absint($item['imagem_id'] ?? 0);
    if (!$imagem_id) {
        $sem_imagem++;
        continue;
    }
    if (!empty($item['imagem'])) {
        $already_ok++;
        continue;
    }
    $url = wp_get_attachment_image_url($imagem_id, 'thumbnail');
    $list[$index]['imagem'] = $url ?: '';
    $updated++;

    if ($updated % 500 === 0) {
        WP_CLI::log("processados $updated novos...");
    }
}

update_option('pressao_candidatos', $list, false);

WP_CLI::log('--- Resumo ---');
WP_CLI::log("Total de linhas: $total");
WP_CLI::log("Já tinham 'imagem' guardada: $already_ok");
WP_CLI::log("Sem imagem_id (nada a fazer): $sem_imagem");
WP_CLI::log("Atualizadas agora: $updated");
