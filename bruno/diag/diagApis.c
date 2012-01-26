/*
 * Copyright 2011 Google Inc. All Rights Reserved.
 *
 * This file provides diagnostics related functions
 *
 */

/*--------------------------------------------------------------------------
 *
 * Includes
 *
 *--------------------------------------------------------------------------
 */

#include "diagdIncludes.h"


/* -------------------------------------------------------------------------
 *
 * Internal defines, types and variables
 *
 *--------------------------------------------------------------------------
 */

/* Host command table */
typedef struct {
  const uint32_t  msgType;        /* refer to diagd_host_req_types_t */
  int       (*CmdFunc)(void); /* ptr to handler for this host cmd */

} diagHostCmdTableEntry;

/* Host command table */
static const diagHostCmdTableEntry diagHostCmdTable[] = {
  /* hostCmdOpcode                      function */
  {DIAGD_REQ_GET_MON_LOG,               &diag_CmdHandler_GetMonitorLog},
  {DIAGD_REQ_GET_DIAG_RESULT_LOG,       &diag_CmdHandler_GetTestResultLog},
  {DIAGD_REQ_RUN_TESTS,                 &diag_CmdHandler_RunTests},

  {DIAGD_REQ_MOCA_GET_CONN_INFO,        &diag_CmdHandler_Moca_GetNodeConnectInfo},
  {DIAGD_REQ_MOCA_GET_MOCA_LOG,         &diag_CmdHandler_Moca_GetMocaLog},
  {DIAGD_REQ_MOCA_GET_MOCA_INITPARMS,   &diag_CmdHandler_Moca_GetInitParams},
  {DIAGD_REQ_MOCA_GET_STATUS,           &diag_CmdHandler_Moca_GetSelfStatus},
  {DIAGD_REQ_MOCA_GET_CONFIG,           &diag_CmdHandler_Moca_GetSelfConfig},
  {DIAGD_REQ_MOCA_GET_NODE_STATUS_TBL,  &diag_CmdHandler_Moca_GetNodeStatus},
  {DIAGD_REQ_MOCA_GET_NODE_STATS_TBL,   &diag_CmdHandler_Moca_GetNodeStatistics},

};


const int numEntriesInHostCmdTable =
              sizeof(diagHostCmdTable) / sizeof(diagHostCmdTableEntry);

const char diagdMsgHeaderMarker[] = {"DIag"};
#define DIAG_MSG_MARKER_LEN       sizeof(uint32_t)


/* -------------------------------------------------------------------------
 *
 * Routines
 *
 *--------------------------------------------------------------------------
 */


/*
 * Send command response
 * NOTE -
 *    The response buffer is shared with request buffer
 *
 * Input:
 * None
 *
 * Output:
 * None
 */
void diag_sendRsp(uint32_t responseCode, uint8_t *pBuf, uint32_t bufLen)
{
  diag_msg_header_t  *pRspHdr = (diag_msg_header_t *)pDiagInfo->hostReqData;
  int   sentHdrLen, bytecount;

  DIAGD_ENTRY("%s: ", __func__);

  /* compose response header */
  bcopy((void *)diagdMsgHeaderMarker,
        (void *)&pRspHdr->headerMarker,
        DIAG_MSG_MARKER_LEN);

  pRspHdr->msgType = responseCode;
  pRspHdr->len     = bufLen;

  DIAGD_TRACE("%s: RspHdr  headerMarker=0x%x, len=%u, msgType=0x%x",
              __func__, pRspHdr->headerMarker, pRspHdr->len, pRspHdr->msgType);

  /* Let's send the response header first */
  sentHdrLen = send(pDiagInfo->hostCmdDesc,
                    pDiagInfo->hostReqData, DIAG_MSG_HDR, 0);
  if (sentHdrLen != DIAG_MSG_HDR) {
    DIAGD_DEBUG("%s: bad length (ExpectedLen=%u, ActualLen=%u\n",
                __func__, DIAG_MSG_HDR, sentHdrLen);
  }

  /* Check if there are payload to be sent */
  if ((pBuf != NULL) && (bufLen > 0)) {

    bytecount = send(pDiagInfo->hostCmdDesc, pBuf, bufLen, 0);
    if (bytecount == -1) {
      DIAGD_DEBUG("%s: Error sending data %s\n", __func__, strerror(errno));
    }
    DIAGD_TRACE("%s: Sent bytes %d\n", __func__, bytecount);
  }

  DIAGD_EXIT("%s: ", __func__);

} /* end of diag_sendRsp */


/*
 * Send the specified file to remote
 * The caller should save the descriptor is in hostCmdDesc field.
 *
 * Input:
 * pFilename   -  Point filename to be sent
 * diagRspCode -  If failed, send a rsp to client to indicate req failed
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
int diag_Sendfile(char *pFilename, uint32_t diagRspCode)
{
  struct stat statBuf;        /* Argument to fstat */
  int   rtn = DIAGD_RC_ERR;   /* Default is failed */
  int   fd;                   /* File descriptor for file to send */
  off_t offset = 0;           /* File offset */
  int   rc;                   /* Return code of system calls */
  int   sentHdrLen;
  diag_msg_header_t  *pRspHdr = (diag_msg_header_t *)pDiagInfo->hostReqData;


  DIAGD_ENTRY("%s: ", __func__);

  do {
    /* Open the file to be sent */
    fd = open(pFilename, O_RDONLY);
    if (fd == -1) {
      DIAGD_DEBUG("%s: open '%s' failed: %s\n",
                  __func__, pFilename, strerror(errno));
      break;
    }

    /* Get the file size */
    fstat(fd, &statBuf);

    /* compose response header */
    bcopy((void *)diagdMsgHeaderMarker,
          (void *)&pRspHdr->headerMarker,
          DIAG_MSG_MARKER_LEN);

    pRspHdr->msgType = diagRspCode;
    pRspHdr->len     = statBuf.st_size;

    DIAGD_TRACE("%s: RspHdr  headerMarker=0x%x, len=%u, msgType=0x%x",
                __func__, pRspHdr->headerMarker,
                pRspHdr->len, pRspHdr->msgType);

    /* Let's send the response header first */
    sentHdrLen = send(pDiagInfo->hostCmdDesc,
                      pDiagInfo->hostReqData, DIAG_MSG_HDR, 0);
    if (sentHdrLen != DIAG_MSG_HDR) {
      DIAGD_DEBUG("%s: bad length (ExpectedLen=%u, ActualLen=%u\n",
                  __func__, DIAG_MSG_HDR, sentHdrLen);
    }

    /* Copy file using sendfile */
    offset = 0;
    rc = sendfile(pDiagInfo->hostCmdDesc, fd, &offset, statBuf.st_size);
    if (rc == -1) {
      DIAGD_DEBUG("%s: sendfile failed: %s\n", __func__, strerror(errno));
      break;
    }

    if (rc != statBuf.st_size) {
      DIAGD_DEBUG("%s: sendfile incomplete: %d of %d bytes sent\n",
                  __func__, rc, (int)statBuf.st_size);
      break;
    }

    rtn = DIAGD_RC_OK;

  } while (false);

  if (fd != -1) {
    /* close descriptor for file that was sent */
    close(fd);
  }

  if (rtn != DIAGD_RC_OK) {
    /* Send rsp back to indicate error occurred */
    diag_sendRsp(diagRspCode, NULL, 0);
  }

  DIAGD_EXIT("%s: ", __func__);

  return(rtn);

} /* end of diag_Sendfile */


/*
 * Run the phy(??)/external(??) loopback test.
 * netIf - device name for loopback test
 *
 * Input:
 * None
 *
 * Output:
 * None
 */
void Diag_runEthLoopBackTest()
{

  DIAGD_ENTRY("%s", __func__);
  diagd_Loopback_Test((char *)ETH0, (uint8_t)DIAG_LOOPBACK_TYPE_INTERNAL);

} /* end of Diag_runEthLoopBackTest */


/*
 * Send diagd monitoring log file to remote
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
int diag_CmdHandler_GetMonitorLog(void)
{
  DIAGD_ENTRY("%s:", __func__);

  return(diag_Sendfile(DIAGD_LOG_FILE, DIAGD_RSP_GET_MON_LOG));

} /* end of diag_CmdHandler_GetMonitorLog */


/*
 * Send diagd test result log file to remote
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
int diag_CmdHandler_GetTestResultLog(void)
{
  DIAGD_ENTRY("%s: ", __func__);

  return(diag_Sendfile(DIAGD_TEST_RESULTS_FILE, DIAGD_RSP_GET_DIAG_RESULT_LOG));

} /* end of diag_CmdHandler_GetTestResultLog */


/*
 * Query to run diagnostics - do the following
 *   1) Send Response to remote that the request received
 *   2) Run tests
 *   3) Reboot
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
int diag_CmdHandler_RunTests(void)
{
  int   rtn = DIAGD_RC_OK;     /* Default is OK */

  /* Send ACK to the client the request was received.
   * The ACK packet just header with DIAGD_RSP_RUN_TESTS
   */
  diag_sendRsp(DIAGD_RSP_RUN_TESTS, NULL, 0);
  diag_CloseFileDesc(&pDiagInfo->hostCmdDesc);
  sleep(5);       /* Give a delay time to send out the ACK */

  /* Start running tests */
  Diag_runEthLoopBackTest();

  /* Reboot */
  DIAGD_TRACE("%s: Issue Reboot command. \n", __func__);
  system("reboot");

  return(rtn);

} /* end of diag_CmdHandler_RunTests */


/*
 * Query to get MoCA init params
 * It is equivalent to "mocactl show --initparms" command.
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_OUT_OF_MEM - Failed
 * others       - refer to enum CmsRet in BRCM cms.h
 */
int diag_CmdHandler_Moca_GetInitParams(void)
{
  MoCA_INITIALIZATION_PARMS  *pInitParms = NULL;
  uint32_t  bufLen = 0;
  int       rtn = DIAGD_RC_OUT_OF_MEM;  /* Default is fail */


  DIAGD_ENTRY("%s", __func__);

  do {
    bufLen = sizeof(MoCA_INITIALIZATION_PARMS);
    pInitParms = malloc(bufLen);
    if (pInitParms != NULL) {
      rtn = diagMoca_GetInitParms(pInitParms);
    }

    if (rtn == DIAGD_RC_OK) {
      /* Send init parameter */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_MOCA_INITPARMS, (uint8_t *)pInitParms, bufLen);
    }
    else {
      /* Failed. Send empty payload to indicate the request failed */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_MOCA_INITPARMS, NULL, 0);
    }

  } while (false);

  if (pInitParms != NULL) {
    free(pInitParms);
  }

  DIAGD_EXIT("%s: rtn=0x%x", __func__, rtn);

  return(rtn);

} /* end of diag_CmdHandler_Moca_GetInitParams */


/*
 * Query to get MoCA self status
 * It is equivalent to "mocactl show --status" command.
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_OUT_OF_MEM - Failed
 * others       - refer to enum CmsRet in BRCM cms.h
 */
int diag_CmdHandler_Moca_GetSelfStatus(void)
{
  MoCA_STATUS   *pSelfNode = NULL;
  uint32_t  bufLen = 0;
  int       rtn = DIAGD_RC_OUT_OF_MEM;  /* Default is fail */


  DIAGD_ENTRY("%s", __func__);

  do {
    bufLen = sizeof(MoCA_STATUS);
    pSelfNode = malloc(bufLen);
    if (pSelfNode != NULL) {
      rtn = diagMoca_GetStatus(pSelfNode);
    }

    if (rtn == DIAGD_RC_OK) {
      /* Send self status to remote */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_STATUS, (uint8_t *)pSelfNode, bufLen);
    }
    else {
      /* Failed. Send empty payload to indicate the request failed */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_STATUS, NULL, 0);
    }

  } while (false);

  if (pSelfNode != NULL) {
    free(pSelfNode);
  }

  DIAGD_EXIT("%s: rtn=0x%x", __func__, rtn);

  return(rtn);

} /* end of diag_CmdHandler_Moca_GetSelfStatus */


/*
 * Query to get MoCA self configuration
 * It is equivalent to "mocactl show --config" command.
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_OUT_OF_MEM - Failed
 * others       - refer to enum CmsRet in BRCM cms.h
 */
int diag_CmdHandler_Moca_GetSelfConfig(void)
{
  diag_moca_config_t *pSelfNode = NULL;
  uint32_t  bufLen = 0;
  int       rtn = DIAGD_RC_OUT_OF_MEM;  /* Default is fail */


  DIAGD_ENTRY("%s", __func__);

  do {
    bufLen = sizeof(diag_moca_config_t);
    pSelfNode = malloc(bufLen);
    if (pSelfNode != NULL) {
      rtn = diagMoca_GetConfig(pSelfNode);
    }

    if (rtn == DIAGD_RC_OK) {
      /* Send self status to remote */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_CONFIG, (uint8_t *)pSelfNode, bufLen);
    }
    else {
      /* Failed. Send empty payload to indicate the request failed */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_CONFIG, NULL, 0);
    }

  } while (false);

  if (pSelfNode != NULL) {
    free(pSelfNode);
  }

  DIAGD_EXIT("%s: rtn=0x%x", __func__, rtn);

  return(rtn);

} /* end of diag_CmdHandler_Moca_GetSelfConfig */


/*
 * Query to get MoCA node status of all conneted nodes
 * It is equivalent to "mocactl showtbl --nodestatus" command.
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_OUT_OF_MEM - Failed
 * others       - refer to enum CmsRet in BRCM cms.h
 */
int diag_CmdHandler_Moca_GetNodeStatus(void)
{
  diag_moca_nodestatus_t   *pNodeStatus = NULL;
  uint32_t  bufLen = 0;
  int       rtn = DIAGD_RC_OUT_OF_MEM;  /* Default is fail */


  DIAGD_ENTRY("%s", __func__);

  do {
    bufLen = sizeof(diag_moca_nodestatus_t);
    pNodeStatus = malloc(bufLen);
    if (pNodeStatus != NULL) {
      rtn = diagMoca_GetNodeStatus(pNodeStatus, &bufLen);
    }

    if (rtn == DIAGD_RC_OK) {
      /* TODO 2011/11/30 -
       * For now, we send the max packet size to remote.
       * We should calculate the valid data length based on connected nodes
       * in diag_moca_nodestatus_t database.
       */
      /* Send node status of the connected nodes to remote */
      diag_sendRsp(DIAGD_RSQ_MOCA_GET_NODE_STATUS_TBL, (uint8_t *)pNodeStatus, bufLen);
    }
    else {
      /* Failed. Send empty payload to indicate the request failed */
      diag_sendRsp(DIAGD_RSQ_MOCA_GET_NODE_STATUS_TBL, NULL, 0);
    }

  } while (false);

  if (pNodeStatus != NULL) {
    free(pNodeStatus);
  }

  DIAGD_EXIT("%s: rtn=0x%x", __func__, rtn);

  return(rtn);

} /* end of diag_CmdHandler_Moca_GetNodeStatus */



/*
 * Query to get MoCA node statistics of all connected nodes
 * It is equivalent to "mocactl showtbl --nodestats" command.
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_OUT_OF_MEM - Failed
 * others       - refer to enum CmsRet in BRCM cms.h
 */
int diag_CmdHandler_Moca_GetNodeStatistics(void)
{
  diag_moca_node_stats_table_t   *pNodeStats = NULL;
  uint32_t  bufLen = 0;
  int       rtn = DIAGD_RC_OUT_OF_MEM;  /* Default is fail */


  DIAGD_ENTRY("%s", __func__);

  do {
    /* Calculate the max size of diag_moca_node_stats_table_t
     * which support up to max connected node
     */
    bufLen = (sizeof(diag_moca_node_stats_entry_t) * MoCA_MAX_NODES) +
             sizeof(uint32_t);

    pNodeStats = malloc(bufLen);
    if (pNodeStats != NULL) {
      rtn = diagMoca_GetNodeStatistics(pNodeStats, (uint16_t *)&bufLen);
    }

    if (rtn == DIAGD_RC_OK) {
      /* Send node statistics to remote */
      diag_sendRsp(DIAGD_RSQ_MOCA_GET_NODE_STATUS_TBL, (uint8_t *)pNodeStats, bufLen);
    }
    else {
      /* Failed. Send empty payload to indicate the request failed */
      diag_sendRsp(DIAGD_RSQ_MOCA_GET_NODE_STATUS_TBL, NULL, 0);
    }

  } while (false);

  if (pNodeStats != NULL) {
    free(pNodeStats);
  }

  DIAGD_EXIT("%s: rtn=0x%x", __func__, rtn);

  return(rtn);

} /* end of diag_CmdHandler_Moca_GetNodeStatistics */


/*
 * Send the moca log file to remote
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
int diag_CmdHandler_Moca_GetMocaLog(void)
{
  DIAGD_ENTRY("%s: ", __func__);

  return(diag_Sendfile(DIAGD_MOCA_LOG_FILE, DIAGD_RSP_MOCA_GET_MOCA_LOG));

} /* end of diag_CmdHandler_Moca_GetMocaLog */


/*
 * Query to get MoCA connection information
 * It is equivalent to "mocactl fmr --a" command.
 *
 * Input:
 * None
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_OUT_OF_MEM - Failed
 * others       - refer to enum CmsRet in BRCM cms.h
 */
int diag_CmdHandler_Moca_GetNodeConnectInfo(void)
{
  diag_moca_node_connect_info_t   *pConnInfo = NULL;
  int   rtn = DIAGD_RC_OUT_OF_MEM;  /* Default is fail */


  DIAGD_ENTRY("%s", __func__);

  do {
    /* Calculate the max size of diag_moca_node_stats_table_t
     * which support up to max connected node
     */
    pConnInfo = malloc(sizeof(diag_moca_node_connect_info_t));
    if (pConnInfo != NULL) {
      rtn = diagMoca_GetConnInfo(pConnInfo);
    }

    if (rtn == DIAGD_RC_OK) {
      /* Send node statistics to remote */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_CONN_INFO, (uint8_t *)pConnInfo,
                   sizeof(diag_moca_node_connect_info_t));
    }
    else {
      /* Failed. Send empty payload to indicate the request failed */
      diag_sendRsp(DIAGD_RSP_MOCA_GET_CONN_INFO, NULL, 0);
    }

  } while (false);

  if (pConnInfo != NULL) {
    free(pConnInfo);
  }

  DIAGD_EXIT("%s: rtn=0x%x", __func__, rtn);

  return(rtn);

} /* end of diag_CmdHandler_Moca_GetNodeConnectInfo */


/*
 * Validate and process the received request
 *
 * Input:
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
int diag_CmdHandler_ProcessReq(void)
{
  int   rtn = DIAGD_RC_ERR;     /* Default is OK */
  int   cmdIdx;
  diag_msg_header_t  *pReqHdr = (diag_msg_header_t *)pDiagInfo->hostReqData;


  DIAGD_ENTRY("%s ", __func__);

  do {

    /* Validate Check msg header marker */
    if (memcmp((void *)&pReqHdr->headerMarker,
               (void *)diagdMsgHeaderMarker, DIAG_MSG_MARKER_LEN) != 0) {
      DIAGD_DEBUG("%s: an invalid request: %s",
                  __func__, (char *)pReqHdr->headerMarker);
      break;
    }

    DIAGD_TRACE("%s: msgType=0x%02X\n", __func__, pReqHdr->msgType);

    for (cmdIdx=0; cmdIdx < numEntriesInHostCmdTable; cmdIdx++) {
      DIAGD_TRACE("%s: Check cmd entry %d (opcode 0x%02X, addr %p)\n",
                  __func__, cmdIdx,
                  diagHostCmdTable[cmdIdx].msgType,
                  diagHostCmdTable[cmdIdx].CmdFunc);
      /* Check host command OpCode. */
      if (pReqHdr->msgType == diagHostCmdTable[cmdIdx].msgType) {
        DIAGD_TRACE("%s: Check cmd entry %d (opcode %02X, addr %p)\n",
                    __func__, cmdIdx, diagHostCmdTable[cmdIdx].msgType,
                    diagHostCmdTable[cmdIdx].CmdFunc);
        DIAGD_TRACE("%s: --> matched cmd entry @ %d\n", __func__, cmdIdx);
        rtn = DIAGD_RC_OK;
        break;
      }
    }
    if (rtn != DIAGD_RC_OK) {
        break;
    }

    /* Run the host command */
    DIAGD_TRACE("exec cmd entry %d\n", cmdIdx);
    pthread_mutex_lock(&lock);
    rtn = (*diagHostCmdTable[cmdIdx].CmdFunc)();
    pthread_mutex_unlock(&lock);

    /* Check return status */
    if (rtn != DIAGD_RC_OK) {
      DIAGD_DEBUG("%s: Command handler failed\n", __func__);
    }

  } while (false);

  DIAGD_EXIT("%s ", __func__);

  return (rtn);

} /* end of diag_CmdHandler_RecvProcReq */


/*
 * This routine is main entry of the diag command handler.
 * Wait for request from remote and process the request
 *
 * Input:
 *
 * Output:
 * DIAGD_RC_OK  - OK
 * DIAGD_RC_ERR - Failed
 */
void diagd_Cmd_Handler()
{
  int   rtn = DIAGD_RC_ERR;     /* Default is OK */
  int   rc;                     /* Return code of system calls */
  struct sockaddr_in addr_in;   /* Socket parameters for accept */
  int   addr_in_len;


  /* 1) Allocate host command buffer
   * 2) open socket and start listen
   */
  if (diag_CmdHandler_Init() != DIAGD_RC_OK) {
    DIAGD_LOG_INFO("Unable to activate host command handler (errno: %s)",
                   strerror(errno));
    return;
  }

  DIAGD_ENTRY("%s: ", __func__);

  do {

    addr_in_len = sizeof (addr_in);

    /* wait for connect */
    pDiagInfo->hostCmdDesc = accept(pDiagInfo->hostCmdSock,
                                    (struct sockaddr *)&addr_in,
                                    (socklen_t *)&addr_in_len);
    if (pDiagInfo->hostCmdDesc == DIAG_FD_NOT_OPEN) {
      DIAGD_DEBUG("%s: accept failed: %s\n", __func__, strerror(errno));
      continue;
    }

    /* Get data from the client */
    rc = recv(pDiagInfo->hostCmdDesc,
              pDiagInfo->hostReqData,
              DIAG_HOSTREQ_BUF_LEN, 0);
    if (rc == -1) {
      DIAGD_DEBUG("%s: recv failed: %s\n", __func__, strerror(errno));
      diag_CloseFileDesc(&pDiagInfo->hostCmdDesc);
      continue;
    }

    /* Check rc. If rc == 0, the remote has performed an orderly shutdown. */
    if (rc > 0) {
      /* Process receive data */
      rtn = diag_CmdHandler_ProcessReq();
    }

    diag_CloseFileDesc(&pDiagInfo->hostCmdDesc);

  } while (true);

  DIAGD_EXIT("%s: ", __func__);

  diag_CmdHandler_Uninit();

} /* diagd_Cmd_Handler */



/* -------------------------------------------------------------------------
 *
 * Routines
 *
 *--------------------------------------------------------------------------
 */

/* -------------------------------------------------------------------------
 * Command Handler related APIs
 *--------------------------------------------------------------------------
 */


/* ======================================================================= */
#if 0
/* ======================================================================= */
int Diag_RdBrcmPhyRegs(TBD)
{
} /* end of Diag_RdBrcmPhyRegs */


/*
 * netIf - device name for loopback test
 * *buf  - (Out) Test result
 */
int Diag_runNandTest(TBD)
{
} /* end of Diag_runNandFlashTest */


/*
 * Network related APIs (MoCA)
 */
/* ======================================================================= */
#endif /* end of 0 */
/* ======================================================================= */

