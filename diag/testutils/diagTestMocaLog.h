void diagMocaStatsLog (bool logging, diag_mocaIf_stats_t *pStats);
void diagMocaPerfStatusLog (bool logging, diag_moca_perf_status_entry_t *pPerfStatus);
void diagMocaNodeStatusLog (bool logging, diag_moca_nodestatus_entry_t *pNodeStatus);
void diagMocaNodeStatsLog (bool logging, diag_moca_node_stats_table_t  *pNodeStats);
void diagMocaMyStatusLog (bool logging, diag_moca_status_t *pStatus);
void diagMoca_log_priority_allocations (bool logging, struct moca_priority_allocations * in);
void diagMoca_log_rlapm_table_100 (bool logging, struct moca_rlapm_table_100 * in);
void diagMoca_log_rlapm_table_50 (bool logging, struct moca_rlapm_table_50 * in);
void diagMoca_log_sapm_table_100 (bool logging, struct moca_sapm_table_100 * in);
void diagMoca_log_sapm_table_50 (bool logging, struct moca_sapm_table_50 * in);
void diagMoca_log_snr_margin_rs (bool logging, struct moca_snr_margin_rs * in);
void diagMoca_log_snr_margin_ldpc (bool logging, struct moca_snr_margin_ldpc * in);
void diagMoca_log_snr_margin_ldpc_pre5 (bool logging, struct moca_snr_margin_ldpc_pre5 * in);
void diagMoca_log_snr_margin_ofdma (bool logging, struct moca_snr_margin_ofdma * in);
void diagMoca_log_snr_margin_table_ldpc (bool logging, struct moca_snr_margin_table_ldpc * in);
void diagMoca_log_snr_margin_table_ldpc_pre5 (bool logging, struct moca_snr_margin_table_ldpc_pre5 * in);
void diagMoca_log_snr_margin_table_ofdma (bool logging, struct moca_snr_margin_table_ofdma * in);
void diagMoca_log_snr_margin_table_rs (bool logging, struct moca_snr_margin_table_rs * in);
void diagMoca_log_start_ulmo (bool logging, struct moca_start_ulmo * in);
