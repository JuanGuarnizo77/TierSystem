"use strict";
var edaEsbuildExportName = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

  // src/index.ts
  var index_exports = {};
  __export(index_exports, {
    activate: () => activate,
    connect: () => connect,
    connectRemoteRelay: () => connectRemoteRelay,
    deactivate: () => deactivate,
    disableAutoConnect: () => disableAutoConnect,
    disconnect: () => disconnect,
    disconnectRemoteRelay: () => disconnectRemoteRelay,
    enableAutoConnect: () => enableAutoConnect,
    showRemoteRelayStatus: () => showRemoteRelayStatus,
    showStatus: () => showStatus,
    toggleAutoConnect: () => toggleAutoConnect
  });

  // src/connection-policy.ts
  var BRIDGE_PORT = 49620;
  var PORT_SCAN_COUNT = 10;
  var PRIMARY_CONNECT_TIMEOUT_MS = 8e3;
  var FALLBACK_CONNECT_TIMEOUT_MS = 1e3;
  var REGISTER_OPEN_CALLBACK_TIMEOUT_MS = 600;
  var RECONNECT_BASE_MS = 500;
  var RECONNECT_MAX_MS = 5e3;
  var HEARTBEAT_INTERVAL_MS = 15e3;
  var HEARTBEAT_LIVENESS_MULTIPLIER = 3;
  var HEARTBEAT_TIMEOUT_MS = HEARTBEAT_INTERVAL_MS * HEARTBEAT_LIVENESS_MULTIPLIER;
  var LOCAL_BRIDGE_HOST = "127.0.0.1";
  function buildLocalBridgeWebSocketUrl(port) {
    const lastBridgePort = BRIDGE_PORT + PORT_SCAN_COUNT - 1;
    if (!Number.isSafeInteger(port) || port < BRIDGE_PORT || port > lastBridgePort) {
      throw new RangeError(`Invalid local bridge port: ${port}`);
    }
    const url = new URL(`http://${LOCAL_BRIDGE_HOST}:${port}/`);
    url.protocol = "ws:";
    return `${url.protocol}//${url.host}`;
  }
  function getLocalBridgeConnectionAttempts(preferredPort2 = BRIDGE_PORT) {
    const range = Array.from({ length: PORT_SCAN_COUNT }, (_, offset) => BRIDGE_PORT + offset);
    const ordered = range.includes(preferredPort2) ? [preferredPort2, ...range.filter((port) => port !== preferredPort2)] : range;
    return ordered.map((port, index) => ({
      port,
      timeoutMs: index === 0 ? PRIMARY_CONNECT_TIMEOUT_MS : FALLBACK_CONNECT_TIMEOUT_MS
    }));
  }
  function reconnectDelayMs(attempt) {
    const safeAttempt = Math.max(1, Math.trunc(attempt));
    return Math.min(RECONNECT_BASE_MS * 2 ** (safeAttempt - 1), RECONNECT_MAX_MS);
  }
  function shouldReconnectAfterSocketFailure({
    wasConnected,
    manualDisconnectRequested: manualDisconnectRequested2,
    autoConnectEnabled: autoConnectEnabled2
  }) {
    return wasConnected && autoConnectEnabled2 && !manualDisconnectRequested2;
  }
  function hasHeartbeatTimedOut(lastServerActivityMs2, nowMs, timeoutMs = HEARTBEAT_TIMEOUT_MS) {
    if (!Number.isFinite(lastServerActivityMs2) || lastServerActivityMs2 <= 0) return false;
    if (!Number.isFinite(nowMs) || nowMs < lastServerActivityMs2) return false;
    return nowMs - lastServerActivityMs2 > timeoutMs;
  }
  function isServerActivityMessage(messageType, heartbeatSource) {
    return messageType !== "heartbeat" || heartbeatSource !== "extension";
  }

  // src/remote-client.ts
  var PROTOCOL_VERSION = "2026-07-remote-relay-v1";
  var DEFAULT_HOSTED_RELAY_URL = "wss://relay.easyeda-mcp-pro.local/session";
  var RECONNECT_BASE_MS2 = 1e3;
  var RECONNECT_MAX_MS2 = 3e4;
  var HEARTBEAT_LIVENESS_MS = 45e3;
  var HEARTBEAT_SWEEP_MS = 15e3;
  var fallbackMessageSequence = 0;
  function makeMessageId() {
    const webCrypto = globalThis.crypto;
    if (typeof webCrypto?.randomUUID === "function") return webCrypto.randomUUID();
    if (typeof webCrypto?.getRandomValues === "function") {
      const bytes = new Uint8Array(16);
      webCrypto.getRandomValues(bytes);
      return `msg_${Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
    }
    fallbackMessageSequence = (fallbackMessageSequence + 1) % Number.MAX_SAFE_INTEGER;
    return `msg_${Date.now().toString(16)}_${fallbackMessageSequence.toString(16)}`;
  }
  function isRecord(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
  }
  function errorToRelayError(error) {
    const record = isRecord(error) ? error : {};
    return {
      code: typeof record.code === "string" ? record.code : "EASYEDA_API_ERROR",
      message: error instanceof Error ? error.message : typeof record.message === "string" ? record.message : String(error),
      suggestion: typeof record.suggestion === "string" ? record.suggestion : "Check EasyEDA Pro and extension logs."
    };
  }
  function nowIso() {
    return (/* @__PURE__ */ new Date()).toISOString();
  }
  var RemoteRelayClient = class {
    constructor(options) {
      this.options = options;
      this.socket = null;
      this.status = { mode: "disabled", state: "disconnected" };
      this.desiredConnection = null;
      this.reconnectTimer = null;
      this.heartbeatTimer = null;
      this.pendingApprovalIds = /* @__PURE__ */ new Set();
    }
    connect(input) {
      this.disconnect("replaced");
      const relayUrl = input.relayUrl ?? DEFAULT_HOSTED_RELAY_URL;
      this.desiredConnection = { ...input, relayUrl };
      this.status = {
        mode: input.mode,
        state: "connecting",
        relayUrl,
        pairingCode: input.pairingCode,
        activeProject: this.options.readActiveProject(),
        reconnectAttempts: 0
      };
      this.options.showToast(`Remote Relay connecting: ${input.mode}`);
      this.openSocket(this.desiredConnection);
    }
    disconnect(reason = "user_disabled") {
      this.desiredConnection = null;
      this.clearReconnectTimer();
      this.clearHeartbeatTimer();
      const socket = this.socket;
      this.socket = null;
      if (socket) {
        try {
          this.sendOnSocket(socket, { type: "session_closed", reason });
          socket.close();
        } catch (error) {
          this.options.log("Remote Relay close failed", error);
        }
      }
      this.status = {
        ...this.status,
        state: "disconnected",
        sessionId: void 0,
        nextReconnectDelayMs: void 0
      };
    }
    getStatus() {
      return {
        ...this.status,
        activeProject: this.options.readActiveProject() ?? this.status.activeProject
      };
    }
    openSocket(input) {
      if (!input.relayUrl) return;
      this.clearReconnectTimer();
      try {
        const socket = this.options.createWebSocket(input.relayUrl);
        this.socket = socket;
        socket.onopen = () => this.handleOpen(socket, input.pairingCode);
        socket.onmessage = (event) => this.handleMessage(socket, event.data);
        socket.onerror = () => this.handleSocketError(socket, "Remote Relay socket error");
        socket.onclose = () => this.handleClose(socket);
      } catch (error) {
        this.socket = null;
        this.scheduleReconnect(`Remote Relay failed to start: ${String(error)}`);
      }
    }
    handleOpen(socket, pairingCode) {
      if (socket !== this.socket) return;
      const timestamp = nowIso();
      this.status = {
        ...this.status,
        state: pairingCode ? "paired" : "connected",
        lastConnectedAt: timestamp,
        lastHeartbeatAt: timestamp,
        nextReconnectDelayMs: void 0,
        lastError: void 0
      };
      this.startHeartbeatTimer();
      this.send({
        type: "register_session",
        extensionVersion: this.options.extensionVersion,
        mode: this.status.mode,
        pairingCode,
        activeProject: this.options.readActiveProject(),
        capabilities: ["local_bridge_proxy"]
      });
      this.options.showToast(
        pairingCode ? "Remote Relay connected and pairing code sent" : "Remote Relay connected"
      );
    }
    handleMessage(socket, data) {
      if (socket !== this.socket) return;
      const text = typeof data === "string" ? data : "";
      let message;
      try {
        message = JSON.parse(text);
      } catch {
        this.options.log("Remote Relay ignored non-JSON message");
        return;
      }
      if (message.protocolVersion !== PROTOCOL_VERSION) {
        this.send({
          type: "error",
          code: "RELAY_VERSION_UNSUPPORTED",
          message: "Unsupported relay protocol version"
        });
        return;
      }
      if (message.type === "session_registered") {
        this.status = {
          ...this.status,
          state: message.paired ? "paired" : "connected",
          sessionId: typeof message.sessionId === "string" ? message.sessionId : this.status.sessionId
        };
        return;
      }
      if (message.type === "heartbeat") {
        this.status = { ...this.status, lastHeartbeatAt: nowIso() };
        this.send({ type: "heartbeat" });
        return;
      }
      if (message.type === "approval_request") {
        void this.handleApprovalRequest(socket, message);
        return;
      }
      if (message.type === "tool_request") {
        void this.handleToolRequest(socket, message);
      }
    }
    async handleApprovalRequest(socket, message) {
      const approvalId = typeof message.approvalId === "string" ? message.approvalId : "";
      const toolName = typeof message.toolName === "string" ? message.toolName : "";
      const actionSummary = typeof message.actionSummary === "string" ? message.actionSummary : toolName || "Remote action";
      const expiresAt = typeof message.expiresAt === "string" ? message.expiresAt : nowIso();
      if (!approvalId || !toolName || this.pendingApprovalIds.has(approvalId)) return;
      this.pendingApprovalIds.add(approvalId);
      let result = "rejected";
      try {
        const requestApproval = this.options.requestApproval;
        if (requestApproval) {
          result = await requestApproval({
            approvalId,
            toolName,
            riskLevel: typeof message.riskLevel === "string" ? message.riskLevel : "write",
            actionSummary,
            inputHash: typeof message.inputHash === "string" ? message.inputHash : "",
            activeProject: isRecord(message.activeProject) ? message.activeProject : void 0,
            expiresAt
          });
        } else {
          this.options.showToast("Remote approval UI is unavailable; request rejected.");
        }
      } catch (error) {
        this.options.log("Remote approval prompt failed", error);
        result = "rejected";
      } finally {
        this.pendingApprovalIds.delete(approvalId);
      }
      this.sendForSocket(socket, {
        type: "approval_result",
        approvalId,
        result
      });
    }
    async handleToolRequest(socket, message) {
      const startedAt = Date.now();
      const toolName = typeof message.toolName === "string" ? message.toolName : "";
      if (!toolName) {
        this.sendForSocket(socket, {
          type: "tool_response",
          requestMessageId: message.messageId,
          ok: false,
          error: {
            code: "REMOTE_TOOL_NAME_MISSING",
            message: "Remote tool request did not include a tool name.",
            suggestion: "Retry with a valid EasyEDA bridge method name."
          },
          durationMs: Date.now() - startedAt
        });
        return;
      }
      if (!this.options.executeToolRequest) {
        this.sendForSocket(socket, {
          type: "tool_response",
          requestMessageId: message.messageId,
          ok: false,
          error: {
            code: "REMOTE_EXECUTION_NOT_ENABLED",
            message: "Remote command dispatch is not enabled in this extension build yet.",
            suggestion: "Use local bridge mode or enable the Remote Relay dispatch integration."
          },
          durationMs: Date.now() - startedAt
        });
        return;
      }
      try {
        const result = await this.options.executeToolRequest(toolName, message.input);
        this.sendForSocket(socket, {
          type: "tool_response",
          requestMessageId: message.messageId,
          ok: true,
          result,
          durationMs: Date.now() - startedAt
        });
      } catch (error) {
        this.sendForSocket(socket, {
          type: "tool_response",
          requestMessageId: message.messageId,
          ok: false,
          error: errorToRelayError(error),
          durationMs: Date.now() - startedAt
        });
      }
    }
    handleSocketError(socket, message) {
      if (socket !== this.socket) return;
      this.status = { ...this.status, lastError: message };
      this.options.log(message);
    }
    handleClose(socket) {
      if (socket !== this.socket) return;
      this.socket = null;
      this.clearHeartbeatTimer();
      if (!this.desiredConnection) {
        if (this.status.state !== "disconnected") {
          this.status = { ...this.status, state: "disconnected", sessionId: void 0 };
          this.options.showToast("Remote Relay disconnected");
        }
        return;
      }
      this.scheduleReconnect("Remote Relay disconnected");
    }
    scheduleReconnect(message) {
      const desired = this.desiredConnection;
      if (!desired) return;
      this.clearHeartbeatTimer();
      this.clearReconnectTimer();
      const nextAttempt = (this.status.reconnectAttempts ?? 0) + 1;
      const delay = Math.min(RECONNECT_BASE_MS2 * 2 ** (nextAttempt - 1), RECONNECT_MAX_MS2);
      this.status = {
        ...this.status,
        state: "connecting",
        sessionId: void 0,
        lastError: message,
        reconnectAttempts: nextAttempt,
        nextReconnectDelayMs: delay
      };
      this.options.log("Remote Relay reconnect scheduled", { attempt: nextAttempt, delayMs: delay });
      this.reconnectTimer = this.options.timers.setTimeout(() => {
        this.reconnectTimer = null;
        if (this.desiredConnection) this.openSocket(desired);
      }, delay);
    }
    startHeartbeatTimer() {
      this.clearHeartbeatTimer();
      this.heartbeatTimer = this.options.timers.setInterval(
        () => this.checkHeartbeatLiveness(),
        HEARTBEAT_SWEEP_MS
      );
    }
    checkHeartbeatLiveness() {
      if (!this.socket || this.socket.readyState !== 1) return;
      const lastHeartbeat = this.status.lastHeartbeatAt ? Date.parse(this.status.lastHeartbeatAt) : void 0;
      if (lastHeartbeat === void 0 || Number.isNaN(lastHeartbeat)) return;
      if (Date.now() - lastHeartbeat <= HEARTBEAT_LIVENESS_MS) return;
      this.options.log("Remote Relay heartbeat stale; closing socket to reconnect");
      try {
        this.socket.close();
      } catch (error) {
        this.options.log("Remote Relay stale socket close failed", error);
        this.scheduleReconnect("Remote Relay heartbeat stale");
      }
    }
    clearReconnectTimer() {
      if (!this.reconnectTimer) return;
      this.options.timers.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    clearHeartbeatTimer() {
      if (!this.heartbeatTimer) return;
      this.options.timers.clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    send(payload) {
      if (!this.socket) return;
      this.sendOnSocket(this.socket, payload);
    }
    sendForSocket(socket, payload) {
      if (socket !== this.socket) return;
      this.sendOnSocket(socket, payload);
    }
    sendOnSocket(socket, payload) {
      if (socket.readyState !== 1) return;
      const envelope = {
        protocolVersion: PROTOCOL_VERSION,
        messageId: makeMessageId(),
        sessionId: this.status.sessionId,
        timestamp: (/* @__PURE__ */ new Date()).toISOString(),
        ...payload
      };
      socket.send(JSON.stringify(envelope));
    }
  };

  // src/utils.ts
  function isRecord2(value) {
    return typeof value === "object" && value !== null;
  }
  function logRecoverableError(context, error) {
    console.warn("[easyeda-mcp-pro]", context, error);
  }
  function safeStringify(value) {
    try {
      return JSON.stringify(value);
    } catch (error) {
      logRecoverableError("failed to stringify log payload", error);
      return String(value);
    }
  }
  function log(message, data) {
    const suffix = data === void 0 ? "" : ` ${safeStringify(data)}`;
    console.log(`[easyeda-mcp-pro ${(/* @__PURE__ */ new Date()).toISOString()}] ${message}${suffix}`);
  }
  var unsafePathSegments = /* @__PURE__ */ new Set(["__proto__", "constructor", "prototype"]);
  function readPropertyDescriptorValue(source, property) {
    let owner = source;
    while (owner) {
      const descriptor = Object.getOwnPropertyDescriptor(owner, property);
      if (descriptor) {
        return "value" in descriptor ? descriptor.value : descriptor.get?.call(source);
      }
      owner = Object.getPrototypeOf(owner);
    }
    return void 0;
  }
  function readPath(source, path) {
    const parts = path.split(".");
    let cursor = source;
    for (const part of parts) {
      if (unsafePathSegments.has(part) || !isRecord2(cursor)) return void 0;
      try {
        cursor = readPropertyDescriptorValue(cursor, part);
      } catch (error) {
        logRecoverableError(`failed to read path segment ${part}`, error);
        return void 0;
      }
      if (cursor === void 0) return void 0;
    }
    return cursor;
  }
  function readPathParent(source, path) {
    const parentPath = path.split(".").slice(0, -1).join(".");
    return parentPath ? readPath(source, parentPath) : source;
  }

  // src/api-introspection.ts
  var API_CLASS_PREFIXES = ["DMT_", "SCH_", "PCB_", "LIB_"];
  var DENIED_API_METHODS = /* @__PURE__ */ new Set([
    "constructor",
    "prototype",
    "__defineGetter__",
    "__defineSetter__"
  ]);
  function withClassNameVariants(paths) {
    const variants = [];
    for (const path of paths) {
      variants.push(path);
      const parts = path.split(".");
      const className = parts[0];
      if (!className) continue;
      const rest = parts.slice(1).join(".");
      const suffix = rest ? `.${rest}` : "";
      const lowerPrefixMatch = /^([a-z]+)_(.+)$/.exec(className);
      const upperPrefixMatch = /^([A-Z]+)_(.+)$/.exec(className);
      if (lowerPrefixMatch?.[1] && lowerPrefixMatch[2]) {
        variants.push(`${lowerPrefixMatch[1].toUpperCase()}_${lowerPrefixMatch[2]}${suffix}`);
      }
      if (upperPrefixMatch?.[1] && upperPrefixMatch[2]) {
        variants.push(`${upperPrefixMatch[1].toLowerCase()}_${upperPrefixMatch[2]}${suffix}`);
      }
    }
    return [...new Set(variants)];
  }
  function normalizeApiClassName(className) {
    const match = /^([a-z]+)_(.+)$/.exec(className);
    if (!match?.[1] || !match[2]) return className;
    return `${match[1].toUpperCase()}_${match[2]}`;
  }
  function isAllowedApiClassName(className) {
    const normalizedClassName = normalizeApiClassName(className);
    return API_CLASS_PREFIXES.some((prefix) => normalizedClassName.startsWith(prefix));
  }
  function isAllowedApiPath(path) {
    const parts = path.split(".");
    if (parts.length !== 2 || !parts[0] || !parts[1]) return false;
    const [className, methodName] = parts;
    if (DENIED_API_METHODS.has(methodName) || methodName.startsWith("__")) return false;
    if (!/^[A-Za-z]+_[A-Za-z0-9]+$/.test(className)) return false;
    if (!/^[A-Za-z]\w*$/.test(methodName)) return false;
    return isAllowedApiClassName(className);
  }
  function getAllPropertyNames(value) {
    const names = [];
    let cursor = value;
    let depth = 0;
    while (isRecord2(cursor) && cursor !== Object.prototype && depth < 8) {
      try {
        names.push(...Object.getOwnPropertyNames(cursor));
      } catch (error) {
        logRecoverableError("failed to read API property names", error);
        break;
      }
      try {
        cursor = Object.getPrototypeOf(cursor);
      } catch (error) {
        logRecoverableError("failed to read API property prototype", error);
        break;
      }
      depth += 1;
    }
    return Array.from(new Set(names)).filter(
      (name) => !["length", "name", "prototype", "constructor"].includes(name)
    );
  }
  function readMember(source, key) {
    if (!isRecord2(source) || !(key in source)) return void 0;
    try {
      return source[key];
    } catch (error) {
      logRecoverableError(`failed to read API member ${key}`, error);
      return void 0;
    }
  }
  function getFunctionNames(value) {
    return getAllPropertyNames(value).filter((name) => {
      const member = readMember(value, name);
      return typeof member === "function";
    });
  }
  function normalizeStateGetters(value, depth, seen) {
    const getterNames = getFunctionNames(value).filter((name) => name.startsWith("getState_"));
    if (getterNames.length === 0) return void 0;
    const state = {};
    for (const getterName of getterNames) {
      const getter = readMember(value, getterName);
      if (typeof getter !== "function") continue;
      try {
        state[getterName.replace(/^getState_/, "")] = normalizeValue(
          getter.call(value),
          depth - 1,
          seen
        );
      } catch (error) {
        state[getterName.replace(/^getState_/, "")] = `ERROR: ${String(error)}`;
      }
    }
    return state;
  }
  function normalizeRecordValue(value, depth, seen) {
    const output = {};
    const ctorName = value.constructor?.name;
    if (ctorName && ctorName !== "Object") output.__class = ctorName;
    const state = normalizeStateGetters(value, depth, seen);
    if (state) output.state = state;
    const methodNames = getFunctionNames(value);
    if (methodNames.length > 0) output.__methods = methodNames;
    for (const key of Object.keys(value)) {
      output[key] = normalizeValue(value[key], depth - 1, seen);
    }
    return output;
  }
  function normalizeObjectValue(value, depth, seen) {
    if (seen.has(value)) return "[Circular]";
    if (depth <= 0) return "[MaxDepth]";
    seen.add(value);
    try {
      if (Array.isArray(value)) {
        return value.map((item) => normalizeValue(item, depth - 1, seen));
      }
      return normalizeRecordValue(value, depth, seen);
    } finally {
      seen.delete(value);
    }
  }
  function normalizeValue(value, depth = 3, seen = /* @__PURE__ */ new WeakSet()) {
    if (value === null) return null;
    if (typeof value === "string") return value;
    if (typeof value === "number") return value;
    if (typeof value === "boolean") return value;
    if (value === void 0) return null;
    if (typeof value === "function") return `[Function ${value.name ?? "anonymous"}]`;
    if (typeof value === "bigint") return value.toString();
    if (typeof value === "symbol") return value.toString();
    return normalizeObjectValue(value, depth, seen);
  }
  function normalizeStandalone(value, depth = 4) {
    return normalizeValue(value, depth, /* @__PURE__ */ new WeakSet());
  }
  function readStateValue(source, stateName, depth = 4) {
    const getter = readMember(source, `getState_${stateName}`);
    if (typeof getter !== "function") return void 0;
    try {
      return normalizeStandalone(getter.call(source), depth);
    } catch (error) {
      return `ERROR: ${String(error)}`;
    }
  }
  function compactPrimitiveSummary(value, stateNames) {
    const state = {};
    for (const stateName of stateNames) {
      state[stateName] = readStateValue(value, stateName, 5);
    }
    return state;
  }

  // src/api-runtime.ts
  function createApiRuntime(toolkit, createBridgeError, globalRoot = globalThis) {
    function getApiCandidates() {
      const candidates = [];
      const edaObj = toolkit.getEda();
      if (edaObj) candidates.push({ name: "eda", root: edaObj });
      const EDAObj = toolkit.getEDA();
      if (EDAObj) candidates.push({ name: "EDA", root: EDAObj });
      const apiObj = toolkit.getApi();
      if (apiObj) candidates.push({ name: "api", root: apiObj });
      candidates.push({ name: "globalThis", root: globalRoot });
      return candidates;
    }
    async function callFirst2(paths, ...args) {
      const allPaths = withClassNameVariants(paths);
      for (const candidate of getApiCandidates()) {
        for (const path of allPaths) {
          const fn = readPath(candidate.root, path);
          if (typeof fn === "function") {
            return await fn.apply(readPathParent(candidate.root, path), args);
          }
        }
      }
      throw createBridgeError(
        "METHOD_NOT_FOUND",
        `No EasyEDA API implementation found for ${paths.join(" or ")}`,
        "Verify the bridge extension supports the installed EasyEDA Pro version."
      );
    }
    function readFirstPath2(paths) {
      for (const candidate of getApiCandidates()) {
        for (const path of withClassNameVariants(paths)) {
          const value = readPath(candidate.root, path);
          if (value !== void 0) return value;
        }
      }
      return void 0;
    }
    async function materializeTaggedPolygonArgument(value, argumentPath) {
      const hasPolygon = "$polygon" in value;
      const hasComplexPolygon = "$complexPolygon" in value;
      if (!hasPolygon && !hasComplexPolygon) return { matched: false };
      if (hasPolygon && hasComplexPolygon) {
        throw createBridgeError(
          "INVALID_PARAMS",
          `Polygon argument has conflicting tags (${argumentPath})`,
          "Use exactly one of {$polygon: [...]} or {$complexPolygon: [...]}.",
          { argumentPath }
        );
      }
      if (Object.keys(value).length !== 1) {
        throw createBridgeError(
          "INVALID_PARAMS",
          `Tagged polygon arguments cannot contain extra fields (${argumentPath})`,
          "Use exactly one tagged polygon field with no additional properties.",
          { argumentPath }
        );
      }
      const tag = hasPolygon ? "$polygon" : "$complexPolygon";
      const source = value[tag];
      if (!Array.isArray(source)) {
        throw createBridgeError(
          "INVALID_PARAMS",
          `${tag} must contain an array (${argumentPath})`,
          `Provide ${tag} as an EasyEDA polygon source array.`,
          { argumentPath }
        );
      }
      const builder = tag === "$polygon" ? ["PCB_MathPolygon.createPolygon", "pcb_MathPolygon.createPolygon"] : ["PCB_MathPolygon.createComplexPolygon", "pcb_MathPolygon.createComplexPolygon"];
      return { matched: true, value: await callFirst2(builder, source) };
    }
    async function materializeApiArgument(value, argumentPath) {
      if (Array.isArray(value)) {
        const output2 = [];
        for (const [index, item] of value.entries()) {
          output2.push(await materializeApiArgument(item, `${argumentPath}[${index}]`));
        }
        return output2;
      }
      if (!isRecord2(value)) return value;
      if ("__class" in value || "__methods" in value) {
        throw createBridgeError(
          "INVALID_PARAMS",
          `Serialized EasyEDA API descriptors cannot be used as call arguments (${argumentPath})`,
          "Pass plain JSON values or an explicit {$polygon: [...]} / {$complexPolygon: [...]} tagged argument.",
          { argumentPath }
        );
      }
      const taggedPolygon = await materializeTaggedPolygonArgument(value, argumentPath);
      if (taggedPolygon.matched) return taggedPolygon.value;
      const output = {};
      for (const [key, nested] of Object.entries(value)) {
        output[key] = await materializeApiArgument(nested, `${argumentPath}.${key}`);
      }
      return output;
    }
    function inspectApiInventory2(filter) {
      const normalizedFilter = filter?.toLowerCase().trim();
      const classMap = /* @__PURE__ */ new Map();
      for (const candidate of getApiCandidates()) {
        const root = candidate.root;
        if (!isRecord2(root)) continue;
        for (const key of Object.getOwnPropertyNames(root)) {
          const className = normalizeApiClassName(key);
          if (!isAllowedApiClassName(className)) continue;
          if (normalizedFilter && !className.toLowerCase().includes(normalizedFilter)) continue;
          const value = readMember(root, key);
          const methods = getFunctionNames(value).sort((a, b) => a.localeCompare(b));
          const existing = classMap.get(className) ?? {
            className,
            runtimePaths: [],
            methods: []
          };
          existing.runtimePaths.push(`${candidate.name}.${key}`);
          existing.methods = Array.from(/* @__PURE__ */ new Set([...existing.methods, ...methods])).sort(
            (a, b) => a.localeCompare(b)
          );
          classMap.set(className, existing);
        }
      }
      const classes = Array.from(classMap.values()).sort(
        (a, b) => a.className.localeCompare(b.className)
      );
      return {
        classes,
        total: classes.length
      };
    }
    async function callAllowedApi2(path, args) {
      if (!isAllowedApiPath(path)) {
        throw createBridgeError(
          "UNAUTHORIZED",
          `API path is not allowed: ${path}`,
          "Use a documented EasyEDA API class method such as SCH_PrimitiveWire.getAll."
        );
      }
      for (const candidate of getApiCandidates()) {
        for (const candidatePath of withClassNameVariants([path])) {
          const fn = readPath(candidate.root, candidatePath);
          if (typeof fn !== "function") continue;
          const parent = readPathParent(candidate.root, candidatePath);
          const materializedArgs = [];
          for (const [index, argument] of args.entries()) {
            materializedArgs.push(await materializeApiArgument(argument, `args[${index}]`));
          }
          const result = await fn.apply(parent, materializedArgs);
          return {
            path,
            resolvedPath: `${candidate.name}.${candidatePath}`,
            result: normalizeValue(result, 5)
          };
        }
      }
      throw createBridgeError(
        "METHOD_NOT_FOUND",
        `No EasyEDA API implementation found for ${path}`,
        "Check easyeda_api_inventory for runtime-supported classes and methods."
      );
    }
    return {
      callFirst: callFirst2,
      readFirstPath: readFirstPath2,
      inspectApiInventory: inspectApiInventory2,
      callAllowedApi: callAllowedApi2
    };
  }

  // src/binary-result.ts
  var MIME_TYPES_BY_EXTENSION = {
    pdf: "application/pdf",
    zip: "application/zip",
    csv: "text/csv",
    txt: "text/plain",
    png: "image/png",
    jpg: "image/jpeg",
    jpeg: "image/jpeg",
    json: "application/json"
  };
  function guessMimeType(fileName) {
    const ext = fileName.split(".").pop()?.toLowerCase();
    return ext && MIME_TYPES_BY_EXTENSION[ext] || "application/octet-stream";
  }
  function isBlobLike(value) {
    return !!value && typeof value === "object" && typeof value.arrayBuffer === "function";
  }
  async function blobToBase64(blob) {
    const buffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const chunkSize = 32768;
    let binary = "";
    for (let i = 0; i < bytes.length; i += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
    }
    return btoa(binary);
  }
  async function normalizeBinaryResult(value, fallbackFileName) {
    if (!isBlobLike(value)) return value;
    const fileName = value.name || fallbackFileName;
    const base64 = await blobToBase64(value);
    return {
      base64,
      mimeType: value.type || guessMimeType(fileName),
      fileName,
      byteLength: value.size
    };
  }

  // src/binary-result-policy.ts
  var DEFAULT_PAYLOAD_SAFETY_MARGIN = 0.6;
  function isBinaryResultPayload(value) {
    return !!value && typeof value === "object" && typeof value.base64 === "string" && typeof value.byteLength === "number";
  }
  function createBinaryResultNormalizer({
    getBridgeMaxPayloadSize,
    createBridgeError,
    normalizeResult = normalizeBinaryResult,
    safetyMargin = DEFAULT_PAYLOAD_SAFETY_MARGIN
  }) {
    return async (value, fallbackFileName) => {
      const normalized = await normalizeResult(value, fallbackFileName);
      if (!isBinaryResultPayload(normalized)) return normalized;
      const maxPayloadSize = getBridgeMaxPayloadSize();
      const budget = Math.floor(maxPayloadSize * safetyMargin);
      if (normalized.byteLength > budget) {
        throw createBridgeError(
          "PAYLOAD_TOO_LARGE",
          `"${normalized.fileName}" is ${normalized.byteLength} bytes, which exceeds the safe transport budget (${budget} bytes, derived from the server's BRIDGE_MAX_PAYLOAD_SIZE=${maxPayloadSize}).`,
          "Increase BRIDGE_MAX_PAYLOAD_SIZE in the MCP server environment, or (for canvas captures) zoom to a smaller region."
        );
      }
      return normalized;
    };
  }

  // src/schematic-read-scope.ts
  var schematicReadScopeValues = ["focused", "page", "all_pages"];
  function scopeError(code, message, suggestion, data) {
    return Object.assign(new Error(message), { code, suggestion, data });
  }
  function normalizedPageUuid(value) {
    if (typeof value !== "string") return void 0;
    const trimmed = value.trim();
    return trimmed || void 0;
  }
  function describeInvalidScope(value) {
    return typeof value === "string" ? value : typeof value;
  }
  function resolveSchematicReadSelector(params = {}, operation = "schematic.read") {
    const rawScope = params.scope;
    const rawPageUuid = params.pageUuid;
    const pageUuid = normalizedPageUuid(rawPageUuid);
    if (rawScope !== void 0 && !schematicReadScopeValues.includes(rawScope)) {
      const requestedScope = describeInvalidScope(rawScope);
      throw scopeError(
        "PAGE_SCOPE_CONFLICT",
        `Invalid schematic read scope for ${operation}.`,
        `Use one of: ${schematicReadScopeValues.join(", ")}.`,
        { operation, requestedScope }
      );
    }
    const explicitScope = rawScope;
    const scope = explicitScope ?? (pageUuid ? "page" : void 0);
    if (rawPageUuid !== void 0 && !pageUuid) {
      throw scopeError(
        "PAGE_UUID_REQUIRED",
        `pageUuid must be a non-empty string for ${operation}.`,
        "Provide a valid schematic page UUID or omit pageUuid.",
        { operation, ...scope ? { requestedScope: scope } : {} }
      );
    }
    if (scope === "page" && !pageUuid) {
      throw scopeError(
        "PAGE_UUID_REQUIRED",
        `scope 'page' requires pageUuid for ${operation}.`,
        "Provide the target schematic page UUID.",
        { operation, requestedScope: scope }
      );
    }
    if (pageUuid && (scope === "focused" || scope === "all_pages")) {
      throw scopeError(
        "PAGE_SCOPE_CONFLICT",
        `pageUuid cannot be combined with scope '${scope}' for ${operation}.`,
        "Use scope 'page' with pageUuid, or omit pageUuid for focused/all_pages.",
        { operation, requestedScope: scope, pageUuid }
      );
    }
    return { scope, pageUuid };
  }
  function assertSchematicReadScopeSupported(params, supported, operation, missingCapability) {
    const selector = resolveSchematicReadSelector(params ?? {}, operation);
    if (!selector.scope || supported.includes(selector.scope)) return selector;
    throw scopeError(
      "PAGE_SCOPE_UNSUPPORTED",
      `Schematic ${selector.scope} scope is not supported for ${operation}.`,
      "Use the focused scope or a tool/runtime capability that explicitly supports the requested scope.",
      {
        requestedScope: selector.scope,
        ...selector.pageUuid ? { pageUuid: selector.pageUuid } : {},
        operation,
        missingCapability
      }
    );
  }
  var focusedScope = ["focused"];
  var focusedAndAllPagesScopes = ["focused", "all_pages"];
  var allMetadataScopes = ["focused", "page", "all_pages"];
  var focusedOnlyCapabilityByOperation = /* @__PURE__ */ new Map([
    ["design.erc", "page-aware-erc"],
    ["schematic.getNetDetail", "page-aware-net-detail-read"],
    ["schematic.listNets", "page-aware-net-read"],
    ["schematic.validateNetlist", "project-wide-complete-netlist-validation"],
    ["system.inspectWires", "page-aware-wire-read"]
  ]);
  function assertSchematicReadOperationScope(params, operation) {
    if (operation === "schematic.getSheetInfo") {
      assertSchematicReadScopeSupported(
        params,
        allMetadataScopes,
        operation,
        "schematic-page-metadata"
      );
      return;
    }
    if (operation === "schematic.listComponents") {
      assertSchematicReadScopeSupported(
        params,
        focusedAndAllPagesScopes,
        operation,
        "page-attributed-component-read"
      );
      return;
    }
    const missingCapability = focusedOnlyCapabilityByOperation.get(operation);
    if (!missingCapability) return;
    assertSchematicReadScopeSupported(params, focusedScope, operation, missingCapability);
  }

  // src/dispatcher-domain-router.ts
  function optionalNumber(value) {
    return typeof value === "number" ? value : void 0;
  }
  function offsetNumber(value) {
    return typeof value === "number" ? value : 0;
  }
  function assertRouterSchematicScope(method, params) {
    assertSchematicReadOperationScope(params, method);
  }
  function createDispatcherDomainRouter(dependencies) {
    const pcbListRoutes = Object.entries({
      "pcb.listComponents": dependencies.pcbReadOperations.listComponents,
      "pcb.listFills": dependencies.pcbReadOperations.listFills,
      "pcb.listRegions": dependencies.pcbReadOperations.listRegions,
      "pcb.listTracks": dependencies.pcbReadOperations.listTracks,
      "pcb.listVias": dependencies.pcbReadOperations.listVias
    }).map(([method, read]) => ({
      method,
      handle: (params) => read(optionalNumber(params.limit), offsetNumber(params.offset))
    }));
    const routes = [
      { method: "api.call", handle: (params) => dependencies.systemApiOperations.apiCall(params) },
      {
        method: "api.execute",
        handle: (params) => dependencies.systemApiOperations.apiExecute(params)
      },
      {
        method: "board.exportGerbers",
        handle: (params) => dependencies.exportOperations.exportGerbers(params)
      },
      { method: "board.getDimensions", handle: () => dependencies.boardInspection.getDimensions() },
      { method: "board.getFeatures", handle: () => dependencies.boardInspection.getFeatures() },
      { method: "board.getStackup", handle: () => dependencies.boardInspection.getStackup() },
      { method: "board.listLayers", handle: () => dependencies.boardInspection.listLayers() },
      { method: "canvas.capture", handle: (params) => dependencies.canvasOperations.capture(params) },
      {
        method: "canvas.captureRegion",
        handle: (params) => dependencies.canvasOperations.captureRegion(params)
      },
      { method: "canvas.locate", handle: (params) => dependencies.canvasOperations.locate(params) },
      { method: "design.drc", handle: () => dependencies.designRuleCheckOperations.runDrc() },
      { method: "design.erc", handle: () => dependencies.designRuleCheckOperations.runErc() },
      {
        method: "design.ruleCheck",
        handle: () => dependencies.designRuleCheckOperations.runRuleCheck()
      },
      {
        method: "export.netlist",
        handle: (params) => dependencies.exportOperations.exportNetlist(params)
      },
      { method: "export.pdf", handle: (params) => dependencies.exportOperations.exportPdf(params) },
      {
        method: "export.pickPlace",
        handle: (params) => dependencies.exportOperations.exportPickPlace(params)
      },
      {
        method: "pcb.addSilkscreenLine",
        handle: (params) => dependencies.pcbWriteOperations.addSilkscreenLine(params)
      },
      { method: "pcb.addText", handle: (params) => dependencies.pcbWriteOperations.addText(params) },
      {
        method: "pcb.addTrack",
        handle: (params) => dependencies.pcbWriteOperations.addTrack(params)
      },
      { method: "pcb.addVia", handle: (params) => dependencies.pcbWriteOperations.addVia(params) },
      {
        method: "pcb.addZone",
        handle: (params) => dependencies.pcbMutationOperations.addZone(params)
      },
      {
        method: "pcb.deleteComponent",
        handle: (params) => dependencies.pcbMutationOperations.deleteComponents(params)
      },
      {
        method: "pcb.exportRouteContext",
        handle: (params) => dependencies.exportOperations.exportRouteContext(params)
      },
      ...pcbListRoutes,
      {
        method: "pcb.modifyComponent",
        handle: (params) => dependencies.pcbMutationOperations.modifyComponent(params)
      },
      {
        method: "pcb.rebuildCopper",
        handle: (params) => dependencies.pcbMutationOperations.rebuildCopper(params)
      },
      {
        method: "project.export",
        handle: (params) => dependencies.projectOperations.export(params)
      },
      { method: "project.open", handle: (params) => dependencies.projectOperations.open(params) },
      { method: "project.save", handle: (params) => dependencies.projectOperations.save(params) },
      {
        method: "bom.generate",
        handle: (params) => dependencies.readOnlyOperations.generateBom(params)
      },
      { method: "bom.validate", handle: () => dependencies.readOnlyOperations.validateBom() },
      {
        method: "inventory.getPrice",
        handle: () => dependencies.readOnlyOperations.inventoryGetPrice()
      },
      { method: "inventory.search", handle: () => dependencies.readOnlyOperations.inventorySearch() },
      {
        method: "library.getDeviceByLcscId",
        handle: (params) => dependencies.readOnlyOperations.getDeviceByLcscId(params)
      },
      {
        method: "schematic.deletePrimitive",
        handle: (params) => dependencies.schematicTransactionOperations.deletePrimitives(params.primitiveIds)
      },
      {
        method: "schematic.getNetDetail",
        handle: (params) => dependencies.readOnlyOperations.getNetDetail(params)
      },
      {
        method: "schematic.getPinNoConnect",
        handle: (params) => dependencies.readOnlyOperations.getPinNoConnect(params)
      },
      {
        method: "schematic.getPrimitiveSnapshot",
        handle: (params) => dependencies.readOnlyOperations.getPrimitiveSnapshot(params)
      },
      {
        method: "schematic.getSheetInfo",
        handle: (params) => dependencies.readOnlyOperations.getSheetInfo(params)
      },
      {
        method: "schematic.listComponents",
        handle: (params) => dependencies.readOnlyOperations.listComponents(params)
      },
      {
        method: "schematic.listNets",
        handle: (params) => dependencies.readOnlyOperations.listNets(params)
      },
      {
        method: "schematic.listPrimitiveIds",
        handle: (params) => dependencies.readOnlyOperations.listPrimitiveIds(params)
      },
      {
        method: "schematic.listRectangles",
        handle: () => dependencies.readOnlyOperations.listRectangles()
      },
      {
        method: "schematic.modifyPrimitive",
        handle: (params) => dependencies.schematicTransactionOperations.modifyPrimitive(
          params.primitiveId,
          params.property || {}
        )
      },
      {
        method: "schematic.primitiveBounds",
        handle: (params) => dependencies.readOnlyOperations.primitiveBounds(params)
      },
      {
        method: "schematic.recreatePrimitiveSnapshot",
        handle: (params) => dependencies.schematicTransactionOperations.recreatePrimitiveSnapshot(params.snapshot)
      },
      {
        method: "schematic.restorePrimitiveSnapshot",
        handle: (params) => dependencies.schematicTransactionOperations.restorePrimitiveSnapshot(params.snapshot)
      },
      {
        method: "schematic.searchDevice",
        handle: (params) => dependencies.readOnlyOperations.searchDevice(params)
      },
      {
        method: "schematic.validateNetlist",
        handle: (params) => dependencies.readOnlyOperations.validateNetlist(params)
      },
      {
        method: "system.apiInventory",
        handle: (params) => dependencies.systemApiOperations.apiInventory(params)
      },
      { method: "system.getStatus", handle: () => dependencies.systemApiOperations.getStatus() },
      {
        method: "system.inspectComponents",
        handle: (params) => dependencies.systemApiOperations.inspectComponents(params)
      },
      {
        method: "system.inspectWires",
        handle: (params) => dependencies.systemApiOperations.inspectWires(params)
      }
    ];
    const methodList = Object.freeze(
      routes.map((route) => route.method).sort((left, right) => left.localeCompare(right))
    );
    return {
      methodList,
      async tryDispatch(method, params = {}) {
        const route = routes.find((candidate) => candidate.method === method);
        if (!route) return { handled: false };
        assertRouterSchematicScope(method, params);
        return { handled: true, value: await route.handle(params) };
      }
    };
  }

  // src/pcb-primitive-state.ts
  function lowerCamel(value) {
    return value.length === 0 ? value : `${value[0]?.toLowerCase()}${value.slice(1)}`;
  }
  function readDirectState(record, key) {
    const candidates = [key, lowerCamel(key), `getState_${key}`];
    for (const candidate of candidates) {
      if (candidate in record && typeof record[candidate] !== "function") {
        return record[candidate];
      }
    }
    return void 0;
  }
  function readPrimitiveState(value, key) {
    if (!isRecord2(value)) return void 0;
    const getter = value[`getState_${key}`];
    if (typeof getter === "function") {
      try {
        const result = getter.call(value);
        if (result !== void 0) return result;
      } catch {
      }
    }
    const direct = readDirectState(value, key);
    if (direct !== void 0) return direct;
    for (const containerName of ["state", "State"]) {
      const container = value[containerName];
      if (!isRecord2(container)) continue;
      const nested = readDirectState(container, key);
      if (nested !== void 0) return nested;
    }
    return void 0;
  }
  function normalizeLayerName(value) {
    return value.trim().toLowerCase().replace(/[\s_-]+/g, " ");
  }
  function isBoardOutlineName(value) {
    const normalized = normalizeLayerName(value);
    return normalized === "11" || normalized === "board outline" || normalized === "board outline layer" || normalized === "boardoutline" || normalized === "boardoutline layer";
  }
  function isBoardOutlineLayer(value) {
    if (value === 11) return true;
    if (typeof value === "string") return isBoardOutlineName(value);
    if (!isRecord2(value)) return false;
    for (const key of ["id", "layerId", "layer", "name", "title", "type", "value", "code"]) {
      if (key in value && isBoardOutlineLayer(value[key])) return true;
    }
    return false;
  }
  function primitiveIsOnBoardOutline(value) {
    const layer = readPrimitiveState(value, "Layer");
    if (isBoardOutlineLayer(layer)) return true;
    for (const key of ["LayerName", "PrimitiveType", "Type", "ObjectType"]) {
      if (isBoardOutlineLayer(readPrimitiveState(value, key))) return true;
    }
    return false;
  }
  function readFiniteNumber(value) {
    return typeof value === "number" && Number.isFinite(value) ? value : void 0;
  }

  // src/board-inspection.ts
  function errorMessage(error) {
    return error instanceof Error ? error.message : String(error);
  }
  var PCB_MIL_TO_MM = 0.0254;
  function roundMetric(value) {
    return Number(value.toFixed(4));
  }
  function pcbMilToMm(value) {
    return roundMetric(value * PCB_MIL_TO_MM);
  }
  function isActivePcbLayerName(name, copperLayerCount) {
    const inner = /^Inner(\d+)$/i.exec(name);
    if (inner) return Number(inner[1]) <= Math.max(0, copperLayerCount - 2);
    if (/^Custom\d+$/i.test(name) || /^Dielectric\d+$/i.test(name)) return false;
    return true;
  }
  async function readCopperLayerCount(pcbLayerClass) {
    if (typeof pcbLayerClass?.getTheNumberOfCopperLayers !== "function") return 0;
    try {
      const value = Number(await pcbLayerClass.getTheNumberOfCopperLayers());
      return Number.isInteger(value) && value >= 2 ? value : 0;
    } catch (error) {
      logRecoverableError("failed to read copper layer count", error);
      return 0;
    }
  }
  function selectPhysicalStackupLayers(physicalStacking) {
    if (Array.isArray(physicalStacking?.layers)) return physicalStacking.layers;
    if (Array.isArray(physicalStacking?.stackup)) return physicalStacking.stackup;
    return [];
  }
  function readBoardThickness(physicalStacking) {
    if (typeof physicalStacking?.thicknessMm === "number") return physicalStacking.thicknessMm;
    if (typeof physicalStacking?.thickness === "number") return physicalStacking.thickness;
    return void 0;
  }
  function createEmptyBoundingBox() {
    return {
      minX: Infinity,
      maxX: -Infinity,
      minY: Infinity,
      maxY: -Infinity
    };
  }
  function updateBoundingBox(bounds, x, y) {
    const finiteX = readFiniteNumber(x);
    const finiteY = readFiniteNumber(y);
    if (finiteX === void 0 || finiteY === void 0) return;
    if (finiteX < bounds.minX) bounds.minX = finiteX;
    if (finiteX > bounds.maxX) bounds.maxX = finiteX;
    if (finiteY < bounds.minY) bounds.minY = finiteY;
    if (finiteY > bounds.maxY) bounds.maxY = finiteY;
  }
  async function readPrimitiveStateResolved(value, key) {
    try {
      return await readPrimitiveState(value, key);
    } catch (error) {
      logRecoverableError(`failed to read primitive state ${key}`, error);
      return void 0;
    }
  }
  async function primitiveIsOnBoardOutlineResolved(value) {
    if (primitiveIsOnBoardOutline(value)) return true;
    if (isBoardOutlineLayer(await readPrimitiveStateResolved(value, "Layer"))) return true;
    for (const key of ["LayerName", "PrimitiveType", "Type", "ObjectType"]) {
      if (isBoardOutlineLayer(await readPrimitiveStateResolved(value, key))) return true;
    }
    return false;
  }
  async function readPointCoordinate(point, key) {
    const state = await readPrimitiveStateResolved(point, key);
    if (state !== void 0) return state;
    if (!isRecord2(point)) return void 0;
    return await point[key.toLowerCase()];
  }
  async function addPoint(bounds, point) {
    if (Array.isArray(point)) {
      updateBoundingBox(bounds, point[0], point[1]);
      return;
    }
    updateBoundingBox(
      bounds,
      await readPointCoordinate(point, "X"),
      await readPointCoordinate(point, "Y")
    );
  }
  async function addPoints(bounds, points) {
    if (!Array.isArray(points)) return false;
    for (const point of points) await addPoint(bounds, point);
    return points.length > 0;
  }
  async function readPolygonSource(polygon) {
    if (typeof polygon.getSource === "function") {
      try {
        const source = await polygon.getSource();
        if (Array.isArray(source)) return source;
      } catch (error) {
        logRecoverableError("failed to read board outline polygon source", error);
      }
    }
    const direct = await polygon.polygon;
    return Array.isArray(direct) ? direct : void 0;
  }
  function readFiniteSourceNumbers(source, startIndex, count) {
    const values = source.slice(startIndex, startIndex + count).map(readFiniteNumber);
    return values.every((value) => value !== void 0) ? values : void 0;
  }
  function addRectangleSourceBounds(bounds, source) {
    if (source.length !== 7) return false;
    const values = readFiniteSourceNumbers(source, 1, 6);
    if (!values) return false;
    const [x, y, width, height, rotation, round] = values;
    if (width < 0 || height < 0 || round < 0 || rotation % 360 !== 0) return false;
    updateBoundingBox(bounds, x, y);
    updateBoundingBox(bounds, x + width, y + height);
    return true;
  }
  function addCircleSourceBounds(bounds, source) {
    if (source.length !== 4) return false;
    const values = readFiniteSourceNumbers(source, 1, 3);
    if (!values) return false;
    const [centerX, centerY, radius] = values;
    if (radius < 0) return false;
    updateBoundingBox(bounds, centerX - radius, centerY - radius);
    updateBoundingBox(bounds, centerX + radius, centerY + radius);
    return true;
  }
  function addLinePolylineSourceBounds(bounds, source) {
    const start = readFiniteSourceNumbers(source, 0, 2);
    if (!start || source[2] !== "L") return false;
    const coordinates = readFiniteSourceNumbers(source, 3, source.length - 3);
    if (!coordinates || coordinates.length < 2 || coordinates.length % 2 !== 0) return false;
    updateBoundingBox(bounds, start[0], start[1]);
    for (let index = 0; index < coordinates.length; index += 2) {
      updateBoundingBox(bounds, coordinates[index], coordinates[index + 1]);
    }
    return true;
  }
  function addRawPolygonSourceBounds(bounds, source) {
    if (source[0] === "R") return addRectangleSourceBounds(bounds, source);
    if (source[0] === "CIRCLE") return addCircleSourceBounds(bounds, source);
    if (readFiniteNumber(source[0]) !== void 0) return addLinePolylineSourceBounds(bounds, source);
    return false;
  }
  async function tryDiscretize(bounds, discretize) {
    if (!discretize) return { added: false };
    try {
      return { added: await addPoints(bounds, await discretize()) };
    } catch (error) {
      return { added: false, error };
    }
  }
  function logPolygonFallbackFailures(instanceError, staticError, source) {
    if (instanceError !== void 0) {
      logRecoverableError("failed to discretize board outline polygon", instanceError);
    }
    if (staticError !== void 0) {
      logRecoverableError(
        "failed to discretize board outline polygon with PCB_MathPolygon",
        staticError
      );
    }
    if (source) {
      logRecoverableError(
        "unsupported board outline polygon source",
        new Error(`Unsupported or malformed polygon source mode: ${String(source[0])}`)
      );
    }
  }
  async function addPolygonPoints(bounds, polygonValue, pcbMathPolygonClass) {
    const polygon = await polygonValue;
    if (!isRecord2(polygon)) return;
    const instanceDiscretize = polygon.discretize;
    const instance = await tryDiscretize(
      bounds,
      typeof instanceDiscretize === "function" ? () => instanceDiscretize.call(polygon) : void 0
    );
    if (instance.added) return;
    const source = await readPolygonSource(polygon);
    const staticDiscretize = pcbMathPolygonClass?.discretize;
    const staticAttempt = await tryDiscretize(
      bounds,
      typeof staticDiscretize === "function" ? () => staticDiscretize.call(pcbMathPolygonClass, source ?? polygon) : void 0
    );
    if (staticAttempt.added) return;
    if (source && addRawPolygonSourceBounds(bounds, source)) return;
    logPolygonFallbackFailures(instance.error, staticAttempt.error, source);
  }
  async function addPrimitivePoints(bounds, primitive, pcbMathPolygonClass) {
    await addPoints(bounds, await readPrimitiveStateResolved(primitive, "Points"));
    await addPolygonPoints(
      bounds,
      readPrimitiveStateResolved(primitive, "Polygon"),
      pcbMathPolygonClass
    );
    updateBoundingBox(
      bounds,
      await readPrimitiveStateResolved(primitive, "StartX"),
      await readPrimitiveStateResolved(primitive, "StartY")
    );
    updateBoundingBox(
      bounds,
      await readPrimitiveStateResolved(primitive, "EndX"),
      await readPrimitiveStateResolved(primitive, "EndY")
    );
  }
  async function addOutlinePrimitiveBounds(primitiveClass, bounds, description, pcbMathPolygonClass) {
    if (!primitiveClass || typeof primitiveClass.getAll !== "function") return;
    try {
      const primitives = await primitiveClass.getAll();
      for (const primitive of primitives || []) {
        if (!await primitiveIsOnBoardOutlineResolved(primitive)) continue;
        await addPrimitivePoints(bounds, primitive, pcbMathPolygonClass);
      }
    } catch (error) {
      logRecoverableError(`failed to read board outline ${description}`, error);
    }
  }
  async function countPrimitiveCollection(pcbClass, description) {
    if (!pcbClass || typeof pcbClass.getAll !== "function") return 0;
    try {
      return (await pcbClass.getAll())?.length || 0;
    } catch (error) {
      logRecoverableError(`failed to count ${description}`, error);
      return 0;
    }
  }
  async function countMountingHoles(pcbPadClass) {
    if (!pcbPadClass || typeof pcbPadClass.getAll !== "function") return 0;
    try {
      let mountingHoles = 0;
      const pads = await pcbPadClass.getAll();
      for (const pad of pads || []) {
        const holeType = await readPrimitiveStateResolved(pad, "HoleType");
        const holeSize = readFiniteNumber(await readPrimitiveStateResolved(pad, "HoleSize")) ?? 0;
        if (holeType === "MountingHole" || holeSize > 2) mountingHoles++;
      }
      return mountingHoles;
    } catch (error) {
      logRecoverableError("failed to read mounting-hole pads", error);
      return 0;
    }
  }
  function createBoardInspectionOperations({
    readFirstPath: readFirstPath2,
    getGlobal: getGlobal2,
    createBridgeError
  }) {
    async function requireActivePcbContext() {
      const dmtPcb = readFirstPath2(["DMT_Pcb", "dmt_Pcb"]);
      if (!dmtPcb || typeof dmtPcb.getCurrentPcbInfo !== "function") {
        return;
      }
      let currentPcb;
      try {
        currentPcb = await dmtPcb.getCurrentPcbInfo();
      } catch (error) {
        throw createBridgeError(
          "CONTEXT_UNAVAILABLE",
          "PCB data is unavailable in the current editor context.",
          "Open and focus a PCB document, then retry.",
          { cause: errorMessage(error) }
        );
      }
      if (!currentPcb) {
        throw createBridgeError(
          "CONTEXT_UNAVAILABLE",
          "No active PCB document is focused.",
          "Open and focus a PCB document, then retry."
        );
      }
    }
    async function listLayers() {
      await requireActivePcbContext();
      const pcbLayerClass = readFirstPath2(["PCB_Layer", "pcb_Layer"]);
      if (!pcbLayerClass || typeof pcbLayerClass.getAllLayers !== "function") {
        throw new Error("pcb_Layer class or getAllLayers method not found");
      }
      const copperLayerCount = await readCopperLayerCount(pcbLayerClass);
      const rawLayers = await pcbLayerClass.getAllLayers();
      const layers = Array.isArray(rawLayers) ? rawLayers : [];
      return layers.filter((layer) => isActivePcbLayerName(String(layer?.name ?? ""), copperLayerCount)).map((layer, index) => ({
        name: layer?.name || "",
        type: layer?.type || "",
        color: layer?.color || "",
        visible: layer?.visible !== false,
        order: typeof layer?.order === "number" && Number.isFinite(layer.order) && layer.order > 0 ? layer.order : index
      }));
    }
    async function getStackup() {
      await requireActivePcbContext();
      const pcbLayerClass = readFirstPath2(["PCB_Layer", "pcb_Layer"]);
      if (!pcbLayerClass) {
        throw new Error("pcb_Layer class not found");
      }
      const totalCopper = await readCopperLayerCount(pcbLayerClass);
      let physicalStacking = null;
      if (typeof pcbLayerClass.getCurrentPhysicalStackingConfiguration === "function") {
        try {
          physicalStacking = await pcbLayerClass.getCurrentPhysicalStackingConfiguration();
        } catch (error) {
          logRecoverableError("failed to read physical stackup", error);
        }
      }
      const rawLayers = selectPhysicalStackupLayers(physicalStacking);
      const layers = rawLayers.map((layer) => ({
        name: layer?.name || "",
        type: layer?.type || "",
        thicknessMm: typeof layer?.thicknessMm === "number" ? layer.thicknessMm : layer?.thickness,
        material: layer?.material || "",
        dielectricConstant: typeof layer?.dielectricConstant === "number" ? layer.dielectricConstant : layer?.dielectric,
        copperWeightOz: typeof layer?.copperWeightOz === "number" ? layer.copperWeightOz : layer?.copperWeight
      }));
      const boardThickness = readBoardThickness(physicalStacking);
      const available = Boolean(physicalStacking && layers.length > 0);
      return {
        totalLayers: totalCopper,
        boardThicknessMm: boardThickness,
        layers,
        available,
        source: available ? "physical_stackup" : "copper_layer_count_only"
      };
    }
    async function getDimensions() {
      await requireActivePcbContext();
      const globalObj = getGlobal2();
      const pcbLineClass = readPath(globalObj, "pcb_PrimitiveLine");
      const pcbArcClass = readPath(globalObj, "pcb_PrimitiveArc");
      const pcbPolylineClass = readPath(globalObj, "pcb_PrimitivePolyline");
      const pcbPadClass = readPath(globalObj, "pcb_PrimitivePad");
      const pcbMathPolygonClass = readFirstPath2(["PCB_MathPolygon", "pcb_MathPolygon"]);
      const bounds = createEmptyBoundingBox();
      await addOutlinePrimitiveBounds(pcbLineClass, bounds, "lines", pcbMathPolygonClass);
      await addOutlinePrimitiveBounds(pcbArcClass, bounds, "arcs", pcbMathPolygonClass);
      await addOutlinePrimitiveBounds(pcbPolylineClass, bounds, "polylines", pcbMathPolygonClass);
      const widthMil = bounds.maxX > bounds.minX ? bounds.maxX - bounds.minX : 0;
      const heightMil = bounds.maxY > bounds.minY ? bounds.maxY - bounds.minY : 0;
      const width = pcbMilToMm(widthMil);
      const height = pcbMilToMm(heightMil);
      const mountingHoles = await countMountingHoles(pcbPadClass);
      const hasOutline = width > 0 && height > 0;
      return {
        widthMm: width,
        heightMm: height,
        shape: hasOutline ? "custom" : void 0,
        mountingHoleCount: mountingHoles,
        areaMm2: roundMetric(width * height),
        hasOutline
      };
    }
    async function getFeatures() {
      await requireActivePcbContext();
      const globalObj = getGlobal2();
      const counts = await Promise.all(
        [
          ["pcb_PrimitiveVia", "vias"],
          ["pcb_PrimitiveLine", "tracks"],
          ["pcb_PrimitivePour", "zones"],
          ["pcb_PrimitiveFill", "fills"],
          ["pcb_PrimitiveRegion", "regions"],
          ["pcb_PrimitivePad", "pads"],
          ["pcb_PrimitiveComponent", "PCB components"]
        ].map(
          ([path, description]) => countPrimitiveCollection(readPath(globalObj, path), description)
        )
      );
      return {
        vias: counts[0],
        tracks: counts[1],
        zones: counts[2],
        fills: counts[3],
        regions: counts[4],
        pads: counts[5],
        components: counts[6]
      };
    }
    return {
      requireActivePcbContext,
      listLayers,
      getStackup,
      getDimensions,
      getFeatures
    };
  }

  // src/canvas-operations.ts
  function createCanvasOperations({
    callFirst: callFirst2,
    normalizeBinaryResult: normalizeBinaryResult2,
    createBridgeError,
    animationRoot = globalThis
  }) {
    function normalizeCanvasRegion(value) {
      const coordinates = [value.left, value.right, value.top, value.bottom];
      if (!coordinates.every(Number.isFinite)) {
        throw createBridgeError(
          "INVALID_PARAMS",
          "Capture region coordinates must be finite numbers.",
          "Provide finite left, right, top, and bottom document coordinates."
        );
      }
      const region = {
        left: Math.min(value.left, value.right),
        right: Math.max(value.left, value.right),
        top: Math.max(value.top, value.bottom),
        bottom: Math.min(value.top, value.bottom)
      };
      if (region.left === region.right || region.top === region.bottom) {
        throw createBridgeError(
          "INVALID_PARAMS",
          "Capture region must have non-zero width and height.",
          "Expand the bounds around the component before capturing it."
        );
      }
      return region;
    }
    async function waitForCanvasPaint() {
      const requestFrame = animationRoot.requestAnimationFrame;
      if (typeof requestFrame === "function") {
        await new Promise((resolve) => {
          let settled = false;
          const finish = () => {
            if (settled) return;
            settled = true;
            clearTimeout(timeout);
            resolve();
          };
          const timeout = setTimeout(finish, 75);
          requestFrame.call(animationRoot, () => requestFrame.call(animationRoot, finish));
        });
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    async function capture(params) {
      const tabId = typeof params.tabId === "string" ? params.tabId : void 0;
      const blob = await callFirst2(["DMT_EditorControl.getCurrentRenderedAreaImage"], tabId);
      return normalizeBinaryResult2(blob, "capture.png");
    }
    async function captureRegion(params) {
      const region = normalizeCanvasRegion(params);
      const tabId = params.tabId;
      const zoomed = await callFirst2(
        ["DMT_EditorControl.zoomToRegion"],
        region.left,
        region.right,
        region.top,
        region.bottom,
        tabId
      );
      if (zoomed === false) {
        throw createBridgeError(
          "EASYEDA_API_ERROR",
          "EasyEDA could not zoom to the requested capture region.",
          "Verify that the target tab is open and the region uses document/canvas coordinates."
        );
      }
      await waitForCanvasPaint();
      const blob = await callFirst2(["DMT_EditorControl.getCurrentRenderedAreaImage"], tabId);
      return normalizeBinaryResult2(blob, "capture-region.png");
    }
    async function locate(params) {
      return callFirst2(
        ["DMT_EditorControl.zoomTo"],
        params.x,
        params.y,
        params.scaleRatio,
        params.tabId
      );
    }
    return { capture, captureRegion, locate };
  }

  // src/design-rule-check-operations.ts
  function normalizeSeverity(raw) {
    const value = raw.toLowerCase();
    if (value.includes("fatal") || value.includes("error")) return "error";
    if (value.includes("warn")) return "warning";
    return "info";
  }
  function scalarString(value) {
    return typeof value === "string" || typeof value === "number" || typeof value === "boolean" || typeof value === "bigint" ? String(value) : void 0;
  }
  function joinScalarValues(values) {
    return values.map(scalarString).filter((value) => value !== void 0).join(" ");
  }
  function firstScalarValue(values) {
    for (const value of values) {
      const scalar = scalarString(value);
      if (scalar !== void 0) return scalar;
    }
    return "unknown";
  }
  function normalizeViolation(item) {
    const obj = item && typeof item === "object" ? { ...item } : {};
    const explanation = obj.explanation && typeof obj.explanation === "object" ? obj.explanation.str : void 0;
    const message = obj.message ?? obj.msg ?? obj.description ?? obj.text ?? obj.detail ?? explanation ?? item;
    const severitySource = joinScalarValues([
      obj.level,
      obj.severity,
      obj.type,
      obj.errorLevel,
      obj.errorType,
      obj.errorObjType,
      obj.name,
      obj.ruleName
    ]);
    let position = obj;
    if (obj.position && typeof obj.position === "object") {
      position = obj.position;
    } else if (obj.location && typeof obj.location === "object") {
      position = obj.location;
    }
    return {
      rule: firstScalarValue([
        obj.rule,
        obj.ruleName,
        obj.ruleTypeName,
        obj.errorType,
        obj.name,
        obj.type
      ]),
      description: typeof message === "string" ? message : JSON.stringify(message),
      severity: normalizeSeverity(severitySource),
      net: obj.net ?? obj.netName ?? void 0,
      component: obj.component ?? obj.ref ?? obj.designator ?? obj.primitiveId ?? void 0,
      location: typeof position.x === "number" && typeof position.y === "number" ? { x: position.x, y: position.y, layer: obj.layer } : void 0
    };
  }
  function normalizeAggregate(obj) {
    if (typeof obj.count !== "number") return null;
    const title = Array.isArray(obj.title) ? joinScalarValues(obj.title) : obj.title;
    const source = joinScalarValues([
      obj.type,
      obj.severity,
      obj.level,
      obj.errorType,
      obj.errorObjType,
      obj.name,
      title
    ]);
    return { severity: normalizeSeverity(source), count: obj.count };
  }
  function hasLeafDetail(obj) {
    return [
      "message",
      "msg",
      "description",
      "text",
      "detail",
      "explanation",
      "errorType",
      "errorObjType",
      "rule",
      "ruleName",
      "ruleTypeName"
    ].some((key) => obj[key] !== void 0);
  }
  function normalizeNode(item) {
    const obj = item && typeof item === "object" ? item : null;
    if (!obj) return { violations: [normalizeViolation(item)], aggregates: [] };
    const children = Array.isArray(obj.list) ? obj.list : [];
    if (children.length > 0) {
      const normalized = children.map(normalizeNode);
      const violations = normalized.flatMap((entry) => entry.violations);
      const aggregates = normalized.flatMap((entry) => entry.aggregates);
      if (violations.length > 0 || aggregates.length > 0) return { violations, aggregates };
    }
    if (hasLeafDetail(obj)) return { violations: [normalizeViolation(obj)], aggregates: [] };
    const aggregate = normalizeAggregate(obj);
    return { violations: [], aggregates: aggregate ? [aggregate] : [] };
  }
  function createDesignRuleCheckOperations(dependencies) {
    async function runNative(paths) {
      const raw = await dependencies.callFirst(paths, true, true, true);
      const normalized = (Array.isArray(raw) ? raw : []).map(normalizeNode);
      const detailed = normalized.flatMap((entry) => entry.violations);
      const aggregates = normalized.flatMap((entry) => entry.aggregates);
      const violations = [
        ...detailed,
        ...aggregates.filter((entry) => entry.count > 0).map((entry) => ({
          rule: "aggregate",
          description: `${entry.count} ${entry.severity}(s) reported by EasyEDA's native design/electrical rule check. Per-violation detail is only shown in EasyEDA Pro when the API returns aggregate counts.`,
          severity: entry.severity
        }))
      ];
      const errorCount = detailed.filter((entry) => entry.severity === "error").length + aggregates.filter((entry) => entry.severity === "error").reduce((sum, entry) => sum + entry.count, 0);
      const warningCount = detailed.filter((entry) => entry.severity === "warning").length + aggregates.filter((entry) => entry.severity === "warning").reduce((sum, entry) => sum + entry.count, 0);
      return {
        violations,
        totalViolations: detailed.length + aggregates.reduce((sum, entry) => sum + entry.count, 0),
        errorCount,
        warningCount,
        passed: errorCount === 0
      };
    }
    async function runSchematicCheck() {
      return runNative(["SCH_Drc.check"]);
    }
    async function runFocusedNative(paths, document2, method) {
      try {
        return await runNative(paths);
      } catch (error) {
        const message = `Focus a ${document2} document, then retry ${method}.`;
        throw dependencies.createBridgeError("CONTEXT_UNAVAILABLE", message, message, {
          cause: dependencies.errorMessage(error)
        });
      }
    }
    async function runDrc() {
      return runFocusedNative(["PCB_Drc.check"], "PCB", "design.drc");
    }
    async function runRuleCheck() {
      let pcbError;
      try {
        return await runNative(["PCB_Drc.check"]);
      } catch (error) {
        pcbError = error;
        dependencies.logRecoverableError(
          "design.ruleCheck: PCB DRC unavailable; trying schematic ERC/DRC",
          error
        );
      }
      try {
        return await runNative(["SCH_Drc.check"]);
      } catch (schematicError) {
        throw dependencies.createBridgeError(
          "CONTEXT_UNAVAILABLE",
          "No active PCB or schematic canvas is available for design.ruleCheck.",
          "Open and focus a PCB or schematic document, then retry.",
          {
            pcbCause: dependencies.errorMessage(pcbError),
            schematicCause: dependencies.errorMessage(schematicError)
          }
        );
      }
    }
    async function runErc() {
      const result = await runFocusedNative(["SCH_Drc.check"], "schematic", "design.erc");
      try {
        const { floatingPins } = await dependencies.findFloatingPins();
        return {
          ...result,
          inferredFloatingPins: floatingPins,
          detailSource: floatingPins.length > 0 ? "inferred_partial" : "native_aggregate_only"
        };
      } catch (error) {
        dependencies.logRecoverableError("design.erc: floating-pin inference failed", error);
        return {
          ...result,
          inferredFloatingPins: [],
          detailSource: "native_aggregate_only"
        };
      }
    }
    return { runDrc, runErc, runRuleCheck, runSchematicCheck };
  }

  // src/export-operations.ts
  function createExportOperations({
    callFirst: callFirst2,
    normalizeBinaryResult: normalizeBinaryResult2,
    createBridgeError
  }) {
    function requireProjectId(params, operation) {
      const projectId = typeof params.projectId === "string" ? params.projectId.trim() : "";
      if (!projectId) {
        throw createBridgeError(
          "INVALID_PARAMS",
          `${operation} requires a non-empty projectId string.`,
          "Provide the current EasyEDA projectId before requesting the export."
        );
      }
      return projectId;
    }
    async function exportGerbers(params) {
      const projectId = requireProjectId(params, "Gerber export");
      return normalizeBinaryResult2(
        await callFirst2(["PCB_ManufactureData.getGerberFile"], projectId),
        "gerbers.zip"
      );
    }
    async function exportRouteContext(params) {
      return normalizeBinaryResult2(
        await callFirst2(
          ["PCB_ManufactureData.getDsnFile"],
          typeof params.fileName === "string" ? params.fileName : void 0
        ),
        "route-context.dsn"
      );
    }
    async function exportPickPlace(params) {
      const projectId = requireProjectId(params, "Pick-and-place export");
      return normalizeBinaryResult2(
        await callFirst2(["PCB_ManufactureData.getPickAndPlaceFile"], projectId),
        `pick-place.${typeof params.format === "string" ? params.format : "csv"}`
      );
    }
    async function exportPdf(params) {
      return normalizeBinaryResult2(
        await callFirst2(
          ["PCB_ManufactureData.getPdfFile", "SCH_ManufactureData.getExportDocumentFile"],
          params.what === "board" ? params : { ...params, type: "schematic" }
        ),
        "export.pdf"
      );
    }
    async function exportNetlist(params) {
      return normalizeBinaryResult2(
        await callFirst2(
          [
            "SCH_Netlist.getNetlist",
            "SCH_ManufactureData.getNetlistFile",
            "PCB_ManufactureData.getNetlistFile"
          ],
          params
        ),
        `netlist.${typeof params.format === "string" ? params.format : "txt"}`
      );
    }
    return {
      exportGerbers,
      exportRouteContext,
      exportPickPlace,
      exportPdf,
      exportNetlist
    };
  }

  // src/pcb-mutation-operations.ts
  var PCB_COMPONENT_TRANSFORM_FIELDS = /* @__PURE__ */ new Set(["layer", "x", "y", "rotation", "primitiveLock"]);
  function validatedComponentTransformProperty(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new TypeError("PCB component transform property must be an object");
    }
    const input = value;
    const output = {};
    for (const [key, fieldValue] of Object.entries(input)) {
      if (!PCB_COMPONENT_TRANSFORM_FIELDS.has(key)) {
        throw new TypeError(`Unsupported PCB component transform field: ${key}`);
      }
      if (key === "primitiveLock") {
        if (typeof fieldValue !== "boolean") {
          throw new TypeError("PCB component primitiveLock must be a boolean");
        }
        output[key] = fieldValue;
        continue;
      }
      if (typeof fieldValue !== "number" || !Number.isFinite(fieldValue)) {
        throw new TypeError(`PCB component ${key} must be a finite number`);
      }
      if (key === "layer" && fieldValue !== 1 && fieldValue !== 2) {
        throw new TypeError("PCB component layer must be 1 (top) or 2 (bottom)");
      }
      output[key] = fieldValue;
    }
    if (Object.keys(output).length === 0) {
      throw new TypeError("PCB component transform must change at least one supported field");
    }
    return output;
  }
  function nativeMethod(target, name) {
    if (target === null || typeof target !== "object" && typeof target !== "function") {
      return void 0;
    }
    const candidate = target[name];
    return typeof candidate === "function" ? candidate : void 0;
  }
  async function invokeNative(target, name, ...args) {
    const method = nativeMethod(target, name);
    if (!method) {
      throw new Error(`EasyEDA runtime does not expose ${name}().`);
    }
    return await method.apply(target, args);
  }
  function nativeStateString(target, getter) {
    const method = nativeMethod(target, getter);
    if (!method) return void 0;
    const value = method.call(target);
    return typeof value === "string" && value.trim().length > 0 ? value : void 0;
  }
  function nativeStateNumber(target, getter) {
    const method = nativeMethod(target, getter);
    if (!method) return void 0;
    const value = method.call(target);
    return typeof value === "number" && Number.isFinite(value) ? value : void 0;
  }
  function nativeItems(value) {
    if (Array.isArray(value)) return value.filter((item) => item !== null && item !== void 0);
    return value === null || value === void 0 ? [] : [value];
  }
  function copperLayer(value) {
    if (value === void 0) return void 0;
    if (typeof value !== "number" || !Number.isInteger(value) || !(value === 1 || value === 2 || value >= 15 && value <= 44)) {
      throw new TypeError(
        "PCB copper rebuild layer must be TOP=1, BOTTOM=2, or INNER_1..INNER_30=15..44."
      );
    }
    return value;
  }
  function requestedPourIds(value) {
    if (value === void 0) return void 0;
    if (!Array.isArray(value) || value.length === 0 || value.some((id) => typeof id !== "string" || id.trim().length === 0)) {
      throw new TypeError("PCB copper rebuild pourIds must be a non-empty array of primitive ids.");
    }
    const ids = value.map((id) => id.trim());
    if (new Set(ids).size !== ids.length) {
      throw new TypeError("PCB copper rebuild pourIds must not contain duplicates.");
    }
    return ids;
  }
  function requestedNet(value) {
    if (value === void 0) return void 0;
    if (typeof value === "string" && value.trim().length > 0) return value.trim();
    throw new TypeError("PCB copper rebuild net must be a non-empty string.");
  }
  function selectPourCandidate(candidates, id) {
    const exact = candidates.find(
      (candidate) => nativeStateString(candidate, "getState_PrimitiveId") === id
    );
    if (exact !== void 0) return exact;
    if (candidates.length === 1) return candidates[0];
    return void 0;
  }
  async function resolvePoursByIds(pourClass, ids) {
    const resolved = [];
    const missing = [];
    for (const id of ids) {
      const candidates = nativeItems(await invokeNative(pourClass, "get", id));
      const selected = selectPourCandidate(candidates, id);
      if (selected === void 0) missing.push(id);
      else resolved.push(selected);
    }
    if (missing.length > 0) {
      throw new Error(
        `PCB pour primitive id(s) not found on the active PCB: ${missing.join(", ")}. No copper was rebuilt.`
      );
    }
    return resolved;
  }
  function validatedPourTarget(primitive, net, layer) {
    const pourId = nativeStateString(primitive, "getState_PrimitiveId");
    if (!pourId) {
      throw new Error(
        "EasyEDA PCB_PrimitivePour returned an item without getState_PrimitiveId(). No copper was rebuilt."
      );
    }
    if (net !== void 0) {
      const actualNet = nativeStateString(primitive, "getState_Net");
      if (actualNet === void 0) {
        throw new Error(
          `PCB pour ${pourId} does not expose getState_Net(); the requested net filter cannot be verified. No copper was rebuilt.`
        );
      }
      if (actualNet !== net) return void 0;
    }
    if (layer !== void 0) {
      const actualLayer = nativeStateNumber(primitive, "getState_Layer");
      if (actualLayer === void 0) {
        throw new Error(
          `PCB pour ${pourId} does not expose getState_Layer(); the requested layer filter cannot be verified. No copper was rebuilt.`
        );
      }
      if (actualLayer !== layer) return void 0;
    }
    if (!nativeMethod(primitive, "rebuildCopperRegion")) {
      throw new Error(
        `PCB pour ${pourId} does not expose rebuildCopperRegion(); no copper was rebuilt.`
      );
    }
    return { pourId, primitive };
  }
  function selectValidatedPours(pours, net, layer) {
    const selected = [];
    for (const primitive of pours) {
      const target = validatedPourTarget(primitive, net, layer);
      if (target) selected.push(target);
    }
    if (selected.length === 0) {
      throw new Error("No existing PCB pours matched the requested filters. No copper was rebuilt.");
    }
    if (new Set(selected.map((item) => item.pourId)).size !== selected.length) {
      throw new Error("EasyEDA returned duplicate PCB pour primitive ids. No copper was rebuilt.");
    }
    return selected;
  }
  async function resolvePours(pourClass, params) {
    const ids = requestedPourIds(params.pourIds);
    const net = requestedNet(params.net);
    const layer = copperLayer(params.layer);
    const pours = ids ? await resolvePoursByIds(pourClass, ids) : nativeItems(await invokeNative(pourClass, "getAll", net, layer));
    return selectValidatedPours(pours, net, layer);
  }
  function pouredReadbackMap(items) {
    const byPourId = /* @__PURE__ */ new Map();
    for (const item of items) {
      const pourId = nativeStateString(item, "getState_PourPrimitiveId");
      const pouredId = nativeStateString(item, "getState_PrimitiveId");
      if (!pourId || !pouredId) continue;
      const current = byPourId.get(pourId) ?? [];
      current.push(pouredId);
      byPourId.set(pourId, current);
    }
    return byPourId;
  }
  function mapReadbackFailureResults(attempts, message) {
    return attempts.map((attempt) => {
      if (attempt.error) {
        return {
          pourId: attempt.pourId,
          pouredId: null,
          status: "error",
          verified: false,
          error: attempt.error
        };
      }
      if (attempt.nativeResult === void 0) {
        return {
          pourId: attempt.pourId,
          pouredId: null,
          status: "no-copper",
          verified: false,
          error: `Native rebuild returned no copper, but PCB_PrimitivePoured read-back failed: ${message}`
        };
      }
      return {
        pourId: attempt.pourId,
        pouredId: null,
        status: "readback-missing",
        verified: false,
        error: `Copper rebuild returned, but PCB_PrimitivePoured read-back failed: ${message}`
      };
    });
  }
  function mapRebuildResults(attempts, postReadback) {
    const byPourId = pouredReadbackMap(postReadback);
    return attempts.map((attempt) => {
      if (attempt.error) {
        return {
          pourId: attempt.pourId,
          pouredId: null,
          status: "error",
          verified: false,
          error: attempt.error
        };
      }
      const readbackIds = byPourId.get(attempt.pourId) ?? [];
      if (attempt.nativeResult === void 0) {
        if (readbackIds.length === 0) {
          return {
            pourId: attempt.pourId,
            pouredId: null,
            status: "no-copper",
            verified: true
          };
        }
        return {
          pourId: attempt.pourId,
          pouredId: readbackIds[0] ?? null,
          status: "readback-mismatch",
          verified: false,
          error: "Native rebuild returned undefined (no copper), but PCB_PrimitivePoured still reports derived copper for this pour."
        };
      }
      if (readbackIds.length === 0) {
        return {
          pourId: attempt.pourId,
          pouredId: null,
          status: "readback-missing",
          verified: false,
          error: "Native rebuild returned a poured result, but PCB_PrimitivePoured.getAll() did not confirm it."
        };
      }
      if (readbackIds.length !== 1) {
        return {
          pourId: attempt.pourId,
          pouredId: readbackIds[0] ?? null,
          status: "readback-mismatch",
          verified: false,
          error: `PCB_PrimitivePoured read-back is ambiguous for this pour (found ${readbackIds.length} derived primitives).`
        };
      }
      const nativePouredId = nativeStateString(attempt.nativeResult, "getState_PrimitiveId");
      if (nativePouredId !== void 0 && nativePouredId !== readbackIds[0]) {
        return {
          pourId: attempt.pourId,
          pouredId: readbackIds[0],
          status: "readback-mismatch",
          verified: false,
          error: `Native rebuild returned poured id ${nativePouredId}, but persisted read-back reported ${readbackIds[0]}.`
        };
      }
      return {
        pourId: attempt.pourId,
        pouredId: readbackIds[0],
        status: "rebuilt",
        verified: true
      };
    });
  }
  function requireCopperRebuildRuntime(readFirstPath2) {
    const pourClass = readFirstPath2(["PCB_PrimitivePour", "pcb_PrimitivePour"]);
    const pouredClass = readFirstPath2(["PCB_PrimitivePoured", "pcb_PrimitivePoured"]);
    if (!pourClass || !nativeMethod(pourClass, "getAll") || !nativeMethod(pourClass, "get")) {
      throw new Error(
        "EasyEDA runtime does not expose PCB_PrimitivePour.get()/getAll(); no copper was rebuilt."
      );
    }
    if (!pouredClass || !nativeMethod(pouredClass, "getAll")) {
      throw new Error(
        "EasyEDA runtime does not expose PCB_PrimitivePoured.getAll(); read-back cannot be verified, so no copper was rebuilt."
      );
    }
    return { pourClass, pouredClass };
  }
  async function readPouredItems(pouredClass) {
    const value = await invokeNative(pouredClass, "getAll");
    if (!Array.isArray(value)) {
      throw new Error("PCB_PrimitivePoured.getAll() did not return an array.");
    }
    return value;
  }
  async function executeCopperRebuilds(targets) {
    const attempts = [];
    for (const target of targets) {
      try {
        attempts.push({
          pourId: target.pourId,
          nativeResult: await invokeNative(target.primitive, "rebuildCopperRegion")
        });
      } catch (error) {
        attempts.push({
          pourId: target.pourId,
          error: error instanceof Error ? error.message : String(error)
        });
        break;
      }
    }
    return attempts;
  }
  function readbackFailureResult(matchedCount, attempts, error) {
    const message = error instanceof Error ? error.message : String(error);
    const results = mapReadbackFailureResults(attempts, message);
    return {
      success: false,
      matchedCount,
      attemptedCount: attempts.length,
      rebuiltCount: 0,
      noCopperCount: results.filter((item) => item.status === "no-copper").length,
      transactionCovered: false,
      planeZonesSupported: false,
      results,
      error: "PCB copper rebuild completed or partially completed, but persisted read-back could not be verified."
    };
  }
  function finalRebuildResult(matchedCount, attempts, results) {
    const rebuiltCount = results.filter((item) => item.status === "rebuilt").length;
    const noCopperCount = results.filter((item) => item.status === "no-copper").length;
    const success = attempts.length === matchedCount && results.length === matchedCount && rebuiltCount === matchedCount;
    const firstFailure = results.find((item) => item.status !== "rebuilt");
    const error = firstFailure?.error ?? (noCopperCount > 0 ? "One or more pours produced no copper and were not counted as successful rebuilds." : "One or more pours could not be rebuilt and verified.");
    return {
      success,
      matchedCount,
      attemptedCount: attempts.length,
      rebuiltCount,
      noCopperCount,
      transactionCovered: false,
      planeZonesSupported: false,
      results,
      ...success ? {} : { error }
    };
  }
  async function rejectUnverifiedZoneCreation(_params) {
    throw new Error(
      "PCB copper-zone creation is unavailable until the complete native contract is verified."
    );
  }
  function createPcbMutationOperations({
    callFirst: callFirst2,
    readFirstPath: readFirstPath2,
    requireActivePcbContext,
    deletePrimitives
  }) {
    async function rebuildCopper(params) {
      await requireActivePcbContext();
      const { pourClass, pouredClass } = requireCopperRebuildRuntime(readFirstPath2);
      const targets = await resolvePours(pourClass, params);
      try {
        await readPouredItems(pouredClass);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const wrapped = new Error(
          `PCB_PrimitivePoured.getAll() preflight failed; read-back cannot be verified, so no copper was rebuilt. ${message}`
        );
        wrapped.cause = error;
        throw wrapped;
      }
      const attempts = await executeCopperRebuilds(targets);
      let postReadback;
      try {
        postReadback = await readPouredItems(pouredClass);
      } catch (error) {
        return readbackFailureResult(targets.length, attempts, error);
      }
      return finalRebuildResult(targets.length, attempts, mapRebuildResults(attempts, postReadback));
    }
    async function modifyComponent(params) {
      return callFirst2(
        ["PCB_PrimitiveComponent.modify", "pcb_PrimitiveComponent.modify"],
        params.primitiveId,
        validatedComponentTransformProperty(params.property)
      );
    }
    async function deleteComponents(params) {
      const ids = Array.isArray(params.primitiveIds) ? params.primitiveIds : [];
      const result = await deletePrimitives(ids);
      return {
        success: result.notFound.length === 0,
        deletedCount: result.deleted.length,
        deleted: result.deleted,
        notFound: result.notFound
      };
    }
    return {
      addZone: rejectUnverifiedZoneCreation,
      rebuildCopper,
      modifyComponent,
      deleteComponents
    };
  }

  // src/pcb-read-operations.ts
  var PCB_DELETABLE_CLASSES = [
    "PCB_PrimitiveComponent",
    "PCB_PrimitiveVia",
    "PCB_PrimitiveLine",
    "PCB_PrimitivePad",
    "PCB_PrimitivePolyline",
    "PCB_PrimitivePour",
    "PCB_PrimitiveArc",
    "PCB_PrimitiveAttribute",
    "PCB_PrimitiveDimension",
    "PCB_PrimitiveFill",
    "PCB_PrimitiveImage",
    "PCB_PrimitiveObject",
    "PCB_PrimitivePoured",
    "PCB_PrimitiveRegion",
    "PCB_PrimitiveString"
  ];
  function paginationEnd(limit, start) {
    return typeof limit === "number" ? start + Math.max(1, limit) : void 0;
  }
  function readPolygonPrimitiveState(readState, value, key) {
    if (value && typeof value === "object") {
      const state = value.state;
      if (state && typeof state === "object") {
        const record = state;
        const lowerCamelKey = key.length > 0 ? key.charAt(0).toLowerCase() + key.slice(1) : key;
        if (key in record) return record[key];
        if (lowerCamelKey in record) return record[lowerCamelKey];
      }
    }
    return readState(value, key);
  }
  async function polygonSource(readState, value) {
    const polygon = readPolygonPrimitiveState(readState, value, "ComplexPolygon");
    if (Array.isArray(polygon)) return polygon;
    if (!polygon || typeof polygon !== "object") return void 0;
    try {
      const getSource = polygon.getSource;
      const source = typeof getSource === "function" ? await getSource.call(polygon) : polygon.polygon;
      return Array.isArray(source) ? source : void 0;
    } catch (error) {
      logRecoverableError("failed to read PCB Fill/Region polygon source", error);
      return void 0;
    }
  }
  function createPcbReadOperations({
    requireActivePcbContext,
    readFirstPath: readFirstPath2,
    readState
  }) {
    async function listComponents(limit, offset = 0) {
      await requireActivePcbContext();
      const pcbCompClass = readFirstPath2(["PCB_PrimitiveComponent", "pcb_PrimitiveComponent"]);
      if (!pcbCompClass || typeof pcbCompClass.getAll !== "function") {
        return { total: 0, items: [] };
      }
      const all = await pcbCompClass.getAll() || [];
      const start = Math.max(0, offset);
      const items = all.slice(start, paginationEnd(limit, start)).map((component) => {
        const footprint = readState(component, "Footprint");
        const device = readState(component, "Component");
        return {
          primitiveId: readState(component, "PrimitiveId") ?? "",
          designator: readState(component, "Designator") ?? "",
          footprintName: footprint?.name ?? "",
          footprintUuid: footprint?.uuid ?? "",
          footprintLibraryUuid: footprint?.libraryUuid ?? "",
          deviceName: device?.name ?? "",
          x: readState(component, "X"),
          y: readState(component, "Y"),
          rotation: readState(component, "Rotation"),
          layer: readState(component, "Layer"),
          locked: readState(component, "PrimitiveLock") ?? false
        };
      });
      return { total: all.length, items };
    }
    async function listPolygonPrimitives(kind, limit, offset = 0) {
      await requireActivePcbContext();
      const pcbClass = readFirstPath2([`PCB_Primitive${kind}`, `pcb_Primitive${kind}`]);
      if (!pcbClass || typeof pcbClass.getAll !== "function") {
        throw new Error(`PCB_Primitive${kind}.getAll is unavailable in this EasyEDA Pro runtime`);
      }
      const all = await pcbClass.getAll() || [];
      const start = Math.max(0, offset);
      const fill = kind === "Fill";
      const items = await Promise.all(
        all.slice(start, paginationEnd(limit, start)).map(async (value) => ({
          primitiveId: readPolygonPrimitiveState(readState, value, "PrimitiveId"),
          layer: readPolygonPrimitiveState(readState, value, "Layer"),
          ...fill ? {
            net: readPolygonPrimitiveState(readState, value, "Net"),
            fillMode: readPolygonPrimitiveState(readState, value, "FillMode")
          } : {
            ruleTypes: readPolygonPrimitiveState(readState, value, "RuleType"),
            regionName: readPolygonPrimitiveState(readState, value, "RegionName")
          },
          lineWidth: readPolygonPrimitiveState(readState, value, "LineWidth"),
          locked: readPolygonPrimitiveState(readState, value, "PrimitiveLock"),
          polygonSource: await polygonSource(readState, value)
        }))
      );
      return { total: all.length, items };
    }
    const listFills = (limit, offset = 0) => listPolygonPrimitives("Fill", limit, offset);
    const listRegions = (limit, offset = 0) => listPolygonPrimitives("Region", limit, offset);
    async function listTracks(limit, offset = 0) {
      await requireActivePcbContext();
      const pcbLineClass = readFirstPath2(["PCB_PrimitiveLine", "pcb_PrimitiveLine"]);
      if (!pcbLineClass || typeof pcbLineClass.getAll !== "function") {
        return { total: 0, items: [] };
      }
      const all = await pcbLineClass.getAll() || [];
      const start = Math.max(0, offset);
      const items = all.slice(start, paginationEnd(limit, start)).map((line) => ({
        primitiveId: readState(line, "PrimitiveId") ?? "",
        net: readState(line, "Net") ?? "",
        layer: readState(line, "Layer"),
        startX: readState(line, "StartX"),
        startY: readState(line, "StartY"),
        endX: readState(line, "EndX"),
        endY: readState(line, "EndY"),
        width: readState(line, "LineWidth"),
        locked: readState(line, "PrimitiveLock") ?? false
      }));
      return { total: all.length, items };
    }
    async function listVias(limit, offset = 0) {
      await requireActivePcbContext();
      const pcbViaClass = readFirstPath2(["PCB_PrimitiveVia", "pcb_PrimitiveVia"]);
      if (!pcbViaClass || typeof pcbViaClass.getAll !== "function") {
        return { total: 0, items: [] };
      }
      const all = await pcbViaClass.getAll() || [];
      const start = Math.max(0, offset);
      const items = all.slice(start, paginationEnd(limit, start)).map((via) => ({
        primitiveId: readState(via, "PrimitiveId") ?? "",
        net: readState(via, "Net") ?? "",
        x: readState(via, "X"),
        y: readState(via, "Y"),
        holeDiameter: readState(via, "HoleDiameter"),
        diameter: readState(via, "Diameter"),
        locked: readState(via, "PrimitiveLock") ?? false
      }));
      return { total: all.length, items };
    }
    async function deletePrimitives(primitiveIds) {
      const remaining = new Set(primitiveIds);
      const deleted = [];
      for (const className of PCB_DELETABLE_CLASSES) {
        if (remaining.size === 0) break;
        const primitiveClass = readFirstPath2([className]);
        if (!primitiveClass || typeof primitiveClass.getAllPrimitiveId !== "function" || typeof primitiveClass.delete !== "function") {
          continue;
        }
        let ownedIds;
        try {
          ownedIds = new Set(await primitiveClass.getAllPrimitiveId() ?? []);
        } catch (error) {
          logRecoverableError(`pcb.deleteComponent: ${className}.getAllPrimitiveId failed`, error);
          continue;
        }
        const matches = [...remaining].filter((id) => ownedIds.has(id));
        if (matches.length === 0) continue;
        try {
          await primitiveClass.delete(matches);
          for (const id of matches) {
            remaining.delete(id);
            deleted.push(id);
          }
        } catch (error) {
          logRecoverableError(`pcb.deleteComponent: ${className}.delete failed`, error);
        }
      }
      return { deleted, notFound: [...remaining] };
    }
    return {
      listComponents,
      listFills,
      listRegions,
      listTracks,
      listVias,
      deletePrimitives
    };
  }

  // src/pcb-write-operations.ts
  function createPcbWriteOperations({
    callFirst: callFirst2,
    extractPrimitiveId: extractPrimitiveId2,
    createBridgeError
  }) {
    async function addTrack(params) {
      const points = Array.isArray(params.points) ? params.points : [];
      if (points.length < 2) {
        throw createBridgeError(
          "INVALID_PARAMS",
          "pcb.addTrack requires at least 2 points",
          "Provide a points array with at least a start and end coordinate."
        );
      }
      const createdIds = [];
      for (let index = 1; index < points.length; index += 1) {
        const start = points[index - 1];
        const end = points[index];
        const created = await callFirst2(
          ["PCB_PrimitiveLine.create", "pcb_PrimitiveLine.create"],
          params.netName,
          params.layer,
          start.x,
          start.y,
          end.x,
          end.y,
          params.width,
          false
        );
        createdIds.push(extractPrimitiveId2(created));
      }
      return { primitiveId: createdIds[0], primitiveIds: createdIds };
    }
    async function addText(params) {
      return callFirst2(
        ["PCB_PrimitiveString.create", "pcb_PrimitiveString.create"],
        params.layer,
        params.x,
        params.y,
        params.text,
        params.fontFamily ?? "NotoSansMonoCJKsc-Regular",
        params.fontSize ?? 1,
        params.lineWidth ?? 0.15,
        params.alignMode ?? 0,
        params.rotation ?? 0,
        params.reverse ?? false,
        params.expansion ?? 0,
        params.mirror ?? false,
        params.locked ?? false
      );
    }
    async function addSilkscreenLine(params) {
      return callFirst2(
        ["PCB_PrimitiveLine.create", "pcb_PrimitiveLine.create"],
        "",
        params.layer,
        params.startX,
        params.startY,
        params.endX,
        params.endY,
        params.lineWidth ?? 0.2,
        false
      );
    }
    async function addVia(params) {
      return callFirst2(
        ["PCB_PrimitiveVia.create", "pcb_PrimitiveVia.create"],
        params.netName,
        params.x,
        params.y,
        params.holeSize,
        params.outerDiameter,
        0,
        "",
        false,
        void 0
      );
    }
    return {
      addTrack,
      addText,
      addSilkscreenLine,
      addVia
    };
  }

  // src/project-operations.ts
  function createProjectOperations({
    callFirst: callFirst2
  }) {
    async function open(params) {
      return callFirst2(["dmt_Project.openProject", "project.open"], params.projectId);
    }
    async function save(_params) {
      return callFirst2([
        "dmt_Workspace.saveAll",
        "dmt_Workspace.saveActiveDocument",
        "sch_Document.save",
        "pcb_Document.save",
        "pnl_Document.save"
      ]);
    }
    async function exportProject(params) {
      return callFirst2(
        ["PCB_ManufactureData.getManufactureData", "SCH_ManufactureData.getExportDocumentFile"],
        params
      );
    }
    return { open, save, export: exportProject };
  }

  // src/read-only-operations.ts
  function optionalNumber2(value) {
    return typeof value === "number" ? value : void 0;
  }
  function offsetNumber2(value) {
    return typeof value === "number" ? value : 0;
  }
  function expectedSnapshotKind(value) {
    return typeof value === "string" ? value : void 0;
  }
  function validatedNetEntry(entry, connectedRefs) {
    const refs = [...new Set((entry.nodes || []).map((node) => node.component))];
    const pins = (entry.nodes || []).map((node) => node.pin);
    for (const ref of refs) connectedRefs.add(ref);
    return { netName: entry.netName, refs, pins, hasNetFlag: true };
  }
  function connectivityWarnings(floatingPins, partRefs, connectedRefs) {
    const warnings = [];
    if (floatingPins.length > 0) {
      warnings.push(`${floatingPins.length} pin(s) are not connected to any net.`);
    }
    if (connectedRefs.size < partRefs.length) {
      warnings.push(`${partRefs.length - connectedRefs.size} component(s) have no net connections.`);
    }
    return warnings;
  }
  async function nativeErcSummary(dependencies, warnings) {
    try {
      const result = await dependencies.runSchematicCheck();
      if (result.errorCount > 0) {
        warnings.push(
          `Native ERC reports ${result.errorCount} error(s): the inferred connectivity above may include pins that overlap without a wire (not truly connected). Run erc_run or check EasyEDA's DRC panel for authoritative, per-violation detail.`
        );
      }
      return {
        errorCount: result.errorCount,
        warningCount: result.warningCount,
        passed: result.passed
      };
    } catch (error) {
      dependencies.logRecoverableError("validateNetlist: native ERC cross-check failed", error);
      return void 0;
    }
  }
  async function validateNetlist(dependencies) {
    const netlistData = await dependencies.listNets();
    const connectedRefs = /* @__PURE__ */ new Set();
    const nets = netlistData.map((entry) => validatedNetEntry(entry, connectedRefs));
    const { floatingPins, partRefs } = await dependencies.findFloatingPins();
    const warnings = connectivityWarnings(floatingPins, partRefs, connectedRefs);
    const nativeErc = await nativeErcSummary(dependencies, warnings);
    return {
      nets,
      floatingPins,
      wiresWithoutNetlist: [],
      nativeErc,
      warnings
    };
  }
  function bomGroupKey(component, groupBy) {
    if (groupBy === "lcsc") return component.lcsc || component.value;
    if (groupBy === "footprint") return component.footprint || "no-footprint";
    return component.value || "no-value";
  }
  function createBomGroup(component) {
    return {
      references: [],
      value: component.value,
      footprint: component.footprint,
      lcsc: component.lcsc,
      manufacturer: component.manufacturer,
      quantity: 0
    };
  }
  async function generateBom(dependencies, params) {
    const result = await dependencies.schematicComponentInspection.listComponents();
    const groupBy = params.groupBy || "value";
    const groups = /* @__PURE__ */ new Map();
    for (const component of result.items) {
      const key = bomGroupKey(component, groupBy);
      const group = groups.get(key) ?? createBomGroup(component);
      if (!groups.has(key)) groups.set(key, group);
      group.references.push(component.reference);
      group.quantity += 1;
    }
    return [...groups.values()].map((group) => ({
      reference: group.references.join(", "),
      value: group.value,
      footprint: group.footprint,
      lcsc: group.lcsc,
      quantity: group.quantity,
      manufacturer: group.manufacturer
    }));
  }
  function createReadOnlyOperations(dependencies) {
    return {
      async listNets(params = {}) {
        assertSchematicReadScopeSupported(
          params,
          ["focused"],
          "schematic.listNets",
          "page-aware-net-read"
        );
        return dependencies.listNets();
      },
      async getNetDetail(params) {
        assertSchematicReadScopeSupported(
          params,
          ["focused"],
          "schematic.getNetDetail",
          "page-aware-net-detail-read"
        );
        return dependencies.getNetDetail(params.netName, params.operationTimeoutMs);
      },
      async getPrimitiveSnapshot(params) {
        return dependencies.schematicTransactionOperations.getPrimitiveSnapshot(
          params.primitiveId,
          expectedSnapshotKind(params.expectedPrimitiveKind)
        );
      },
      async listPrimitiveIds(params) {
        return dependencies.schematicTransactionOperations.listPrimitiveIds(params.primitiveKind);
      },
      async listComponents(params) {
        const selector = assertSchematicReadScopeSupported(
          params,
          ["focused", "all_pages"],
          "schematic.listComponents",
          "page-attributed-component-read"
        );
        let allPages = params.allPages;
        if (selector.scope === "focused") allPages = false;
        if (selector.scope === "all_pages") allPages = true;
        return dependencies.schematicComponentInspection.listComponents(
          optionalNumber2(params.limit),
          offsetNumber2(params.offset),
          allPages
        );
      },
      async getSheetInfo(params = {}) {
        assertSchematicReadScopeSupported(
          params,
          ["focused", "page", "all_pages"],
          "schematic.getSheetInfo",
          "schematic-page-metadata"
        );
        return dependencies.schematicInspection.getSheetInfo(params);
      },
      async primitiveBounds(params) {
        return dependencies.schematicInspection.primitiveBounds(params.primitiveIds);
      },
      async searchDevice(params) {
        return dependencies.callFirst(
          ["LIB_Device.search", "lib_Device.search"],
          params.key,
          params.libraryUuid,
          params.classification,
          params.symbolType,
          params.itemsOfPage,
          params.page
        );
      },
      async listRectangles() {
        return dependencies.schematicInspection.listRectangles();
      },
      async getPinNoConnect(params) {
        return dependencies.getPinNoConnect(params.primitiveId, params.pinNumber);
      },
      async validateNetlist(params = {}) {
        assertSchematicReadScopeSupported(
          params,
          ["focused"],
          "schematic.validateNetlist",
          "project-wide-complete-netlist-validation"
        );
        return validateNetlist(dependencies);
      },
      async getDeviceByLcscId(params) {
        const lcscId = String(params.lcscId ?? "");
        const libraryUuid = typeof params.libraryUuid === "string" ? params.libraryUuid : void 0;
        return dependencies.callFirst(["LIB_Device.getByLcscIds"], [lcscId], libraryUuid, false);
      },
      async generateBom(params) {
        return generateBom(dependencies, params);
      },
      async validateBom() {
        const result = await dependencies.schematicComponentInspection.listComponents();
        return { totalParts: result.items.length, missing: [], obsolete: [], alternates: [] };
      },
      async inventorySearch() {
        return [];
      },
      async inventoryGetPrice() {
        return null;
      }
    };
  }

  // src/system-api-operations.ts
  function enumerableKeys(value) {
    const keys = [];
    for (const key in value) keys.push(key);
    return keys;
  }
  function collectAllPropertyNames(value, logRecoverableError2) {
    let props = [];
    let current = value;
    while (current && current !== Object.prototype) {
      try {
        props = props.concat(Object.getOwnPropertyNames(current));
      } catch (error) {
        logRecoverableError2("failed to read debug probe property names", error);
      }
      try {
        current = Object.getPrototypeOf(current);
      } catch (error) {
        logRecoverableError2("failed to read debug probe prototype", error);
        break;
      }
    }
    return Array.from(new Set(props)).filter(
      (property) => !["length", "name", "prototype", "constructor"].includes(property)
    );
  }
  function recordOwnKeys(globals, value, key, errorKey) {
    try {
      globals[key] = Object.getOwnPropertyNames(value);
    } catch (error) {
      globals[errorKey] = String(error);
    }
  }
  function recordEnumerableKeys(globals, value, key, errorKey) {
    try {
      globals[key] = enumerableKeys(value);
    } catch (error) {
      globals[errorKey] = String(error);
    }
  }
  function recordRuntimeClassKeys(globals, edaObject, property, outputKey, errorKey, logRecoverableError2) {
    try {
      const runtimeClass = edaObject[property];
      if (runtimeClass) {
        globals[outputKey] = collectAllPropertyNames(runtimeClass, logRecoverableError2);
      }
    } catch (error) {
      globals[errorKey] = String(error);
    }
  }
  function recordEdaDiagnostics(globals, edaObject, logRecoverableError2) {
    recordOwnKeys(globals, edaObject, "eda_keys", "eda_keys_err");
    recordEnumerableKeys(globals, edaObject, "eda_for_in_keys", "eda_for_in_keys_err");
    recordRuntimeClassKeys(
      globals,
      edaObject,
      "sch_PrimitiveComponent",
      "sch_PrimitiveComponent_all_keys",
      "sch_PrimitiveComponent_err",
      logRecoverableError2
    );
    recordRuntimeClassKeys(
      globals,
      edaObject,
      "sch_Document",
      "sch_Document_all_keys",
      "sch_Document_err",
      logRecoverableError2
    );
    recordRuntimeClassKeys(
      globals,
      edaObject,
      "pcb_Document",
      "pcb_Document_all_keys",
      "pcb_Document_err",
      logRecoverableError2
    );
    recordRuntimeClassKeys(
      globals,
      edaObject,
      "dmt_Schematic",
      "dmt_Schematic_all_keys",
      "dmt_Schematic_err",
      logRecoverableError2
    );
    recordRuntimeClassKeys(
      globals,
      edaObject,
      "dmt_Project",
      "dmt_Project_all_keys",
      "dmt_Project_err",
      logRecoverableError2
    );
    recordRuntimeClassKeys(
      globals,
      edaObject,
      "dmt_Pcb",
      "dmt_Pcb_all_keys",
      "dmt_Pcb_err",
      logRecoverableError2
    );
  }
  function matchesEasyEdaDiagnosticKey(key) {
    const lower = key.toLowerCase();
    return lower.includes("dmt") || lower.includes("eda") || lower.includes("schematic") || lower.includes("pcb") || lower.includes("api");
  }
  function recordGlobalDiagnostics(globals) {
    try {
      globals.globalThis_matched_keys = Object.getOwnPropertyNames(globalThis).filter(
        matchesEasyEdaDiagnosticKey
      );
    } catch (error) {
      globals.globalThis_keys_err = String(error);
    }
    try {
      globals.globalThis_for_in_matched_keys = enumerableKeys(globalThis).filter(
        matchesEasyEdaDiagnosticKey
      );
    } catch (error) {
      globals.globalThis_for_in_err = String(error);
    }
  }
  function collectStatusGlobals(toolkit, logRecoverableError2) {
    const globals = {};
    const edaObject = toolkit.getEda();
    const EDAObject = toolkit.getEDA();
    const apiObject = toolkit.getApi();
    try {
      globals.typeof_api = typeof globalThis.api;
      globals.typeof_eda = typeof globalThis.eda;
      globals.typeof_EDA = typeof globalThis.EDA;
      globals.typeof_local_api = typeof apiObject;
      globals.typeof_local_eda = typeof edaObject;
      globals.typeof_local_EDA = typeof EDAObject;
      if (edaObject) {
        recordEdaDiagnostics(globals, Object(edaObject), logRecoverableError2);
      }
      if (EDAObject) {
        const boxedEDAObject = Object(EDAObject);
        recordOwnKeys(globals, boxedEDAObject, "EDA_keys", "EDA_keys_err");
        recordEnumerableKeys(globals, boxedEDAObject, "EDA_for_in_keys", "EDA_for_in_keys_err");
      }
      recordGlobalDiagnostics(globals);
    } catch (error) {
      globals.error = String(error);
    }
    return { globals, edaObject, EDAObject };
  }
  function createSystemApiOperations(dependencies) {
    return {
      async apiCall(params) {
        return dependencies.callAllowedApi(
          typeof params.path === "string" ? params.path : "",
          Array.isArray(params.args) ? params.args : []
        );
      },
      async apiExecute(params) {
        const code = typeof params.code === "string" ? params.code : "";
        if (!code.trim()) {
          throw dependencies.createBridgeError(
            "INVALID_PARAMS",
            "code is required",
            "Provide JavaScript code to execute"
          );
        }
        const AsyncFunction = Object.getPrototypeOf(async function() {
        }).constructor;
        const edaGlobal = dependencies.toolkit.getEda() ?? globalThis.eda;
        const fn = new AsyncFunction("eda", code);
        const result = await fn(edaGlobal);
        return { result: normalizeValue(result, 5) };
      },
      async apiInventory(params) {
        return dependencies.inspectApiInventory(
          typeof params.filter === "string" ? params.filter : void 0
        );
      },
      async getStatus() {
        const { globals, edaObject, EDAObject } = collectStatusGlobals(
          dependencies.toolkit,
          dependencies.logRecoverableError
        );
        const hasDMTLocal = isRecord2(edaObject) && "DMT_Schematic" in edaObject;
        const hasDMTEDA = isRecord2(EDAObject) && "DMT_Schematic" in EDAObject;
        return {
          bridgeVersion: dependencies.toolkit.getBridgeVersion(),
          capabilities: [...dependencies.methodList],
          devMode: false,
          globals,
          hasEda: !!edaObject || !!EDAObject,
          hasDMT: "DMT_Schematic" in globalThis || hasDMTLocal || hasDMTEDA,
          dispatcherBuildId: dependencies.buildId
        };
      },
      async inspectComponents(params) {
        const limit = typeof params.limit === "number" ? params.limit : 5;
        const schCompClass = dependencies.readFirstPath([
          "SCH_PrimitiveComponent",
          "SCH_PrimitiveComponent3",
          "sch_PrimitiveComponent"
        ]);
        if (!schCompClass || typeof schCompClass.getAll !== "function") {
          throw new Error("SCH_PrimitiveComponent.getAll is not available in this EasyEDA runtime");
        }
        const comps = await schCompClass.getAll(void 0, true);
        const items = Array.isArray(comps) ? comps : [];
        return {
          total: items.length,
          samples: items.slice(0, Math.max(1, Math.min(limit, 25))).map((item) => normalizeValue(item, 5))
        };
      },
      async inspectWires(params) {
        const limit = typeof params.limit === "number" ? params.limit : 10;
        const offset = typeof params.offset === "number" ? params.offset : 0;
        const schWireClass = dependencies.readFirstPath([
          "SCH_PrimitiveWire",
          "SCH_PrimitiveWire3",
          "sch_PrimitiveWire"
        ]);
        if (!schWireClass || typeof schWireClass.getAll !== "function") {
          throw new Error("SCH_PrimitiveWire.getAll is not available in this EasyEDA runtime");
        }
        const wires = await schWireClass.getAll();
        const items = Array.isArray(wires) ? wires : [];
        const start = Math.max(0, offset);
        const end = start + Math.max(1, Math.min(limit, 50));
        return {
          total: items.length,
          samples: items.slice(start, end).map(dependencies.summarizeWirePrimitive)
        };
      }
    };
  }

  // src/schematic-component-inspection.ts
  function nativeScalarString(value) {
    return typeof value === "string" || typeof value === "number" || typeof value === "boolean" || typeof value === "bigint" ? String(value) : "";
  }
  function readOtherPropertyValue(otherProperty, key) {
    if (!otherProperty) return void 0;
    const exact = nativeScalarString(otherProperty[key]).trim();
    if (exact) return exact;
    const normalizedKey = key.trim().toLowerCase();
    for (const [candidateKey, candidateValue] of Object.entries(otherProperty)) {
      const value = nativeScalarString(candidateValue).trim();
      if (candidateKey.trim().toLowerCase() === normalizedKey && value) return value;
    }
    return void 0;
  }
  function resolveComponentDisplayValue(rawName, otherProperty, manufacturerId, deviceName) {
    const name = nativeScalarString(rawName).trim();
    const expression = /^=\{(.+)\}$/.exec(name);
    if (expression) {
      const propertyName = expression[1].trim();
      const propertyValue = readOtherPropertyValue(otherProperty, propertyName);
      if (propertyValue) return propertyValue;
      if (propertyName.toLowerCase() === "manufacturer part" && manufacturerId) {
        return manufacturerId;
      }
      return manufacturerId || deviceName || name;
    }
    if (name) return name;
    return readOtherPropertyValue(otherProperty, "Value") || manufacturerId || deviceName || "";
  }
  function readRecordState(component, key, readState) {
    const value = readState(component, key);
    return isRecord2(value) ? value : void 0;
  }
  function createSchematicComponentInspectionOperations({
    readFirstPath: readFirstPath2,
    readState
  }) {
    function isBomComponent(component) {
      const componentType = nativeScalarString(readState(component, "ComponentType")).toLowerCase();
      if (componentType === "sheet" || componentType === "netflag" || componentType === "netport") {
        return false;
      }
      const deviceName = nativeScalarString(readRecordState(component, "Component", readState)?.name);
      return !deviceName.startsWith("Drawing-Symbol_");
    }
    async function resolveFootprint(component, otherProperty, footprintClass) {
      const footprintInfo = readRecordState(component, "Footprint", readState);
      let footprint = nativeScalarString(footprintInfo?.name).trim();
      if (!footprint && footprintInfo?.uuid && footprintClass) {
        try {
          const resolved = await footprintClass.get(footprintInfo.uuid, footprintInfo.libraryUuid);
          footprint = nativeScalarString(isRecord2(resolved) ? resolved.name : void 0).trim();
        } catch (error) {
          logRecoverableError("failed to resolve component footprint", error);
        }
      }
      return footprint || readOtherPropertyValue(otherProperty, "Footprint") || readOtherPropertyValue(otherProperty, "Supplier Footprint") || "";
    }
    async function mapComponent(component, footprintClass) {
      const device = readRecordState(component, "Component", readState);
      const symbol = readRecordState(component, "Symbol", readState);
      const otherProperty = readRecordState(component, "OtherProperty", readState);
      const manufacturerId = nativeScalarString(readState(component, "ManufacturerId"));
      const deviceName = nativeScalarString(device?.name);
      return {
        primitiveId: nativeScalarString(readState(component, "PrimitiveId")),
        reference: nativeScalarString(readState(component, "Designator")),
        value: resolveComponentDisplayValue(
          readState(component, "Name"),
          otherProperty,
          manufacturerId,
          deviceName
        ),
        footprint: await resolveFootprint(component, otherProperty, footprintClass),
        lcsc: nativeScalarString(readState(component, "SupplierId")),
        manufacturer: nativeScalarString(readState(component, "Manufacturer")),
        manufacturerId,
        datasheet: readOtherPropertyValue(otherProperty, "Datasheet") || readOtherPropertyValue(otherProperty, "datasheet") || "",
        deviceUuid: nativeScalarString(device?.uuid),
        deviceLibraryUuid: nativeScalarString(device?.libraryUuid),
        deviceName,
        symbolName: nativeScalarString(symbol?.name),
        x: readState(component, "X"),
        y: readState(component, "Y"),
        rotation: readState(component, "Rotation")
      };
    }
    async function listComponents(limit, offset = 0, allPages) {
      const componentClass = readFirstPath2(["SCH_PrimitiveComponent", "SCH_PrimitiveComponent3", "sch_PrimitiveComponent"]);
      const footprintClass = readFirstPath2(["LIB_Footprint", "lib_Footprint"]);
      if (!componentClass) {
        throw new Error("SCH_PrimitiveComponent class not found in EasyEDA Pro API");
      }
      const all = await componentClass.getAll(void 0, allPages !== false) || [];
      const bom = all.filter(isBomComponent);
      const total = bom.length;
      const start = Math.max(0, offset);
      const end = typeof limit === "number" ? start + Math.max(1, limit) : void 0;
      const selected = bom.slice(start, end);
      const items = [];
      for (const component of selected) {
        items.push(await mapComponent(component, footprintClass));
      }
      return { total, items };
    }
    return { listComponents };
  }

  // src/schematic-inspection.ts
  function asNonEmptyRecord(value) {
    if (!isRecord2(value) || Object.keys(value).length === 0) return void 0;
    return value;
  }
  function asRecordArray(value) {
    if (!Array.isArray(value)) return [];
    return value.filter((item) => isRecord2(item));
  }
  function nativeScalarString2(value) {
    return typeof value === "string" || typeof value === "number" || typeof value === "boolean" || typeof value === "bigint" ? String(value) : "";
  }
  function readFocusedPageUuid(focusedDocument) {
    const uuid = focusedDocument?.uuid;
    return typeof uuid === "string" && uuid.trim() ? uuid : void 0;
  }
  function mergeSchematicPages(pages, currentSchematic) {
    if (pages.length > 0) return pages;
    const schematicPages = asRecordArray(currentSchematic?.page);
    return schematicPages.length > 0 ? schematicPages : pages;
  }
  function resolveCurrentPage(currentPage, focusedDocumentPage, focusedPageUuid, pages, currentSchematic) {
    if (currentPage) return { currentPage, source: "current_page" };
    if (focusedDocumentPage) {
      return { currentPage: focusedDocumentPage, source: "focused_document" };
    }
    const matchedPage = focusedPageUuid ? pages.find((page) => page.uuid === focusedPageUuid) : void 0;
    if (matchedPage) return { currentPage: matchedPage, source: "focused_document" };
    if (pages.length === 1 && currentSchematic) {
      return { currentPage: pages[0], source: "current_schematic_page_list" };
    }
    return {};
  }
  function createSchematicInspectionOperations({
    callFirst: callFirst2,
    readFirstPath: readFirstPath2,
    readState,
    extractPrimitiveId: extractPrimitiveId2,
    createBridgeError
  }) {
    async function primitiveBounds(primitiveIds) {
      const schematicPrimitiveClass = readFirstPath2(["SCH_Primitive", "sch_Primitive"]);
      if (!schematicPrimitiveClass) {
        throw new Error("SCH_Primitive class not found in EasyEDA Pro API");
      }
      const ids = Array.isArray(primitiveIds) ? primitiveIds.filter((id) => typeof id === "string" && id.length > 0) : [];
      const items = [];
      for (const id of ids) {
        let bounds = null;
        try {
          bounds = await schematicPrimitiveClass.getPrimitivesBBox([id]) ?? null;
        } catch (error) {
          logRecoverableError(`failed to read bounding box for primitive ${id}`, error);
        }
        items.push({ primitiveId: id, bounds });
      }
      let combined = null;
      if (ids.length > 0) {
        try {
          combined = await schematicPrimitiveClass.getPrimitivesBBox(ids) ?? null;
        } catch (error) {
          logRecoverableError("failed to read combined bounding box", error);
        }
      }
      return { items, combined };
    }
    async function trySheetInfoCall(stage, paths, attempts, ...args) {
      try {
        const value = normalizeValue(await callFirst2(paths, ...args), 5);
        const meaningful = Array.isArray(value) ? value.length > 0 : Boolean(asNonEmptyRecord(value)) || value !== null && value !== void 0;
        attempts.push({ stage, status: meaningful ? "value" : "empty" });
        return value;
      } catch (error) {
        attempts.push({
          stage,
          status: "unavailable",
          error: error instanceof Error ? error.message : String(error)
        });
        return void 0;
      }
    }
    async function readSheetPages(attempts) {
      const currentPages = asRecordArray(
        await trySheetInfoCall(
          "current_page_list",
          ["DMT_Schematic.getCurrentSchematicAllSchematicPagesInfo"],
          attempts
        )
      );
      if (currentPages.length > 0) return currentPages;
      return asRecordArray(
        await trySheetInfoCall("all_page_list", ["DMT_Schematic.getAllSchematicPagesInfo"], attempts)
      );
    }
    async function readCurrentSchematicIfNeeded(currentPage, pages, attempts) {
      if (currentPage && pages.length > 0) return void 0;
      return asNonEmptyRecord(
        await trySheetInfoCall(
          "current_schematic",
          ["DMT_Schematic.getCurrentSchematicInfo"],
          attempts
        )
      );
    }
    async function readFocusedDocumentPage(currentPage, focusedPageUuid, attempts) {
      if (currentPage || !focusedPageUuid) return void 0;
      return asNonEmptyRecord(
        await trySheetInfoCall(
          "focused_document_page",
          ["DMT_Schematic.getSchematicPageInfo"],
          attempts,
          focusedPageUuid
        )
      );
    }
    async function resolveRequestedPageScope(pageUuid, context) {
      const { initialCurrentPage, pages, focusedPageUuid, focusedDocument, attempts } = context;
      const diagnostics = {
        stage: "page_scope_resolution",
        requestedScope: "page",
        requestedPageUuid: pageUuid,
        focusedPageUuid,
        currentPageAvailable: Boolean(initialCurrentPage),
        pageListAvailable: pages.length > 0,
        focusedDocumentAvailable: Boolean(focusedDocument),
        attempts
      };
      if (!pages.length) {
        throw createBridgeError(
          "PAGE_SCOPE_UNAVAILABLE",
          "EasyEDA did not expose a schematic page list for the requested page scope.",
          "Focus a schematic in the target project and retry after page metadata becomes available.",
          {
            requestedScope: "page",
            pageUuid,
            focusedPageUuid,
            operation: "schematic.getSheetInfo",
            missingCapability: "schematic-page-metadata",
            diagnostics
          }
        );
      }
      const listedPage = pages.find((page) => page.uuid === pageUuid);
      if (!listedPage) {
        throw createBridgeError(
          "PAGE_NOT_FOUND",
          `Schematic page "${pageUuid}" was not found in the current project page list.`,
          "Refresh the schematic page list and use a page UUID returned by EasyEDA.",
          {
            requestedScope: "page",
            pageUuid,
            focusedPageUuid,
            operation: "schematic.getSheetInfo"
          }
        );
      }
      const directPageCandidate = asNonEmptyRecord(
        await trySheetInfoCall(
          "requested_page",
          ["DMT_Schematic.getSchematicPageInfo"],
          attempts,
          pageUuid
        )
      );
      const directPage = directPageCandidate?.uuid === pageUuid ? directPageCandidate : void 0;
      return {
        currentPage: directPage ?? listedPage,
        pages,
        source: directPage ? "requested_page" : "page_list",
        focusedDocument,
        diagnostics
      };
    }
    function resolveAllPagesScope(context) {
      const { initialCurrentPage, pages, focusedPageUuid, focusedDocument, attempts } = context;
      const diagnostics = {
        stage: "all_pages_scope_resolution",
        requestedScope: "all_pages",
        focusedPageUuid,
        currentPageAvailable: Boolean(initialCurrentPage),
        pageListAvailable: pages.length > 0,
        focusedDocumentAvailable: Boolean(focusedDocument),
        attempts
      };
      if (!pages.length) {
        throw createBridgeError(
          "PAGE_SCOPE_UNAVAILABLE",
          "EasyEDA did not expose a schematic page list for all-pages scope.",
          "Focus a schematic in the target project and retry after page metadata becomes available.",
          {
            requestedScope: "all_pages",
            focusedPageUuid,
            operation: "schematic.getSheetInfo",
            missingCapability: "schematic-page-metadata",
            diagnostics
          }
        );
      }
      const currentPage = initialCurrentPage ?? (focusedPageUuid ? pages.find((page) => page.uuid === focusedPageUuid) : void 0);
      return {
        currentPage,
        pages,
        source: initialCurrentPage ? "current_page" : "page_list",
        focusedDocument,
        diagnostics
      };
    }
    async function getSheetInfo(params = {}) {
      const selector = resolveSchematicReadSelector(params, "schematic.getSheetInfo");
      const attempts = [];
      const initialCurrentPage = asNonEmptyRecord(
        await trySheetInfoCall(
          "current_page",
          ["DMT_Schematic.getCurrentSchematicPageInfo"],
          attempts
        )
      );
      const initialPages = await readSheetPages(attempts);
      const focusedDocument = asNonEmptyRecord(
        await trySheetInfoCall(
          "focused_document",
          ["DMT_SelectControl.getCurrentDocumentInfo"],
          attempts
        )
      );
      const focusedPageUuid = readFocusedPageUuid(focusedDocument);
      const currentSchematic = await readCurrentSchematicIfNeeded(
        initialCurrentPage,
        initialPages,
        attempts
      );
      const pages = mergeSchematicPages(initialPages, currentSchematic);
      const context = { initialCurrentPage, pages, focusedPageUuid, focusedDocument, attempts };
      if (selector.scope === "page") {
        return resolveRequestedPageScope(selector.pageUuid, context);
      }
      if (selector.scope === "all_pages") {
        return resolveAllPagesScope(context);
      }
      const focusedDocumentPage = await readFocusedDocumentPage(
        initialCurrentPage,
        focusedPageUuid,
        attempts
      );
      const resolution = resolveCurrentPage(
        initialCurrentPage,
        focusedDocumentPage,
        focusedPageUuid,
        pages,
        currentSchematic
      );
      const diagnostics = {
        stage: "focused_sheet_resolution",
        currentPageAvailable: Boolean(resolution.currentPage),
        pageListAvailable: pages.length > 0,
        focusedDocumentAvailable: Boolean(focusedDocument),
        attempts
      };
      if (!resolution.currentPage) {
        throw createBridgeError(
          "SHEET_INFO_UNAVAILABLE",
          "EasyEDA did not expose metadata for the focused schematic page.",
          "Focus the schematic editor tab and retry. The diagnostics identify which runtime paths were empty or unavailable.",
          diagnostics
        );
      }
      return {
        currentPage: resolution.currentPage,
        pages,
        source: resolution.source,
        focusedDocument,
        diagnostics
      };
    }
    async function listRectangles() {
      const schematicRectangleClass = readFirstPath2(["SCH_PrimitiveRectangle", "sch_PrimitiveRectangle"]);
      if (!schematicRectangleClass || typeof schematicRectangleClass.getAll !== "function") {
        return { total: 0, items: [] };
      }
      let all;
      try {
        all = await schematicRectangleClass.getAll() || [];
      } catch (error) {
        logRecoverableError("failed to list rectangles", error);
        all = [];
      }
      const items = all.map((rectangle) => {
        const rawY = readState(rectangle, "TopLeftY") ?? readState(rectangle, "Y");
        return {
          primitiveId: extractPrimitiveId2(rectangle) || nativeScalarString2(readState(rectangle, "PrimitiveId")),
          x: readState(rectangle, "TopLeftX") ?? readState(rectangle, "X"),
          y: typeof rawY === "number" ? -rawY : rawY,
          width: readState(rectangle, "Width"),
          height: readState(rectangle, "Height"),
          rotation: readState(rectangle, "Rotation")
        };
      });
      return { total: items.length, items };
    }
    return { primitiveBounds, getSheetInfo, listRectangles };
  }

  // src/schematic-snapshot-recreation.ts
  var SUPPORTED_KINDS = Object.freeze([
    "circle",
    "polygon",
    "rectangle",
    "text",
    "wire"
  ]);
  function requiredSnapshotNumber(property, key, createBridgeError) {
    const value = property[key];
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw createBridgeError(
        "INVALID_PARAMS",
        `Snapshot property ${key} must be a finite number`,
        "Pass an unmodified snapshot returned by schematic.getPrimitiveSnapshot."
      );
    }
    return value;
  }
  function createSchematicSnapshotRecreator(dependencies) {
    const { callFirst: callFirst2, createBridgeError, requirePublicTextAlignMode: requirePublicTextAlignMode2 } = dependencies;
    const requiredNumber = (property, key) => requiredSnapshotNumber(property, key, createBridgeError);
    async function create(snapshot) {
      const property = snapshot.property;
      switch (snapshot.primitiveKind) {
        case "wire":
          return callFirst2(
            ["SCH_PrimitiveWire.create", "sch_PrimitiveWire.create"],
            property.line,
            property.net,
            property.color,
            property.lineWidth,
            property.lineType
          );
        case "text": {
          const rawY = requiredNumber(property, "y");
          return callFirst2(
            ["SCH_PrimitiveText.create", "sch_PrimitiveText.create"],
            requiredNumber(property, "x"),
            -rawY,
            property.content,
            property.rotation ?? 0,
            property.color ?? "#000000",
            property.fontName ?? "Arial",
            property.fontSize ?? 20,
            property.bold ?? false,
            property.italic ?? false,
            property.underline ?? false,
            requirePublicTextAlignMode2(property.alignMode, "snapshot.property.alignMode")
          );
        }
        case "rectangle": {
          const rawY = requiredNumber(property, "y");
          return callFirst2(
            ["SCH_PrimitiveRectangle.create", "sch_PrimitiveRectangle.create"],
            requiredNumber(property, "x"),
            -rawY,
            requiredNumber(property, "width"),
            requiredNumber(property, "height"),
            property.cornerRadius ?? 0,
            property.rotation ?? 0,
            property.color ?? "#000000",
            property.fillColor ?? "none",
            property.lineWidth ?? 1,
            property.lineType ?? 0,
            property.fillStyle ?? "none"
          );
        }
        case "circle":
          return callFirst2(
            ["SCH_PrimitiveCircle.create", "sch_PrimitiveCircle.create"],
            requiredNumber(property, "centerX"),
            requiredNumber(property, "centerY"),
            requiredNumber(property, "radius"),
            property.color ?? "#000000",
            property.fillColor ?? "none",
            property.lineWidth ?? 1,
            property.lineType ?? 0,
            property.fillStyle ?? "none"
          );
        case "polygon":
          return callFirst2(
            ["SCH_PrimitivePolygon.create", "sch_PrimitivePolygon.create"],
            property.line,
            property.color ?? "#000000",
            property.fillColor ?? "none",
            property.lineWidth ?? 1,
            property.lineType ?? 0
          );
        case "component":
        case "netflag":
        case "netport":
          throw createBridgeError(
            "UNSUPPORTED_RUNTIME",
            `Delete rollback is not supported for ${snapshot.primitiveKind} primitives`,
            "Use transaction-backed modify, or avoid deleting components/net flags/net ports until a complete creation descriptor is available."
          );
      }
    }
    return { supportedKinds: SUPPORTED_KINDS, create };
  }

  // src/schematic-transaction-operations.ts
  var NOT_HANDLED = { handled: false };
  var COMPONENT_CLASS_PATHS = [
    "SCH_PrimitiveComponent",
    "SCH_PrimitiveComponent3",
    "sch_PrimitiveComponent"
  ];
  var WIRE_CLASS_PATHS = ["SCH_PrimitiveWire", "SCH_PrimitiveWire3", "sch_PrimitiveWire"];
  var TEXT_CLASS_PATHS = ["SCH_PrimitiveText", "sch_PrimitiveText"];
  var RECTANGLE_CLASS_PATHS = ["SCH_PrimitiveRectangle", "sch_PrimitiveRectangle"];
  var CIRCLE_CLASS_PATHS = ["SCH_PrimitiveCircle", "sch_PrimitiveCircle"];
  var POLYGON_CLASS_PATHS = ["SCH_PrimitivePolygon", "sch_PrimitivePolygon"];
  function handled(value) {
    return { handled: true, value };
  }
  function pointKey(point) {
    return `${Math.round(point.x * 1e3) / 1e3},${Math.round(point.y * 1e3) / 1e3}`;
  }
  function shiftWireLine(rawLine, targetKeys, dx, dy) {
    if (!Array.isArray(rawLine) || rawLine.length === 0) return null;
    let changed = false;
    if (Array.isArray(rawLine[0])) {
      const updated = rawLine.map((pair) => {
        if (!Array.isArray(pair) || pair.length < 2) return pair;
        const [x, y, ...rest] = pair;
        if (!targetKeys.has(pointKey({ x, y }))) return pair;
        changed = true;
        return [x + dx, y + dy, ...rest];
      });
      return changed ? { line: updated } : null;
    }
    const flat = rawLine.slice();
    for (let i = 0; i + 1 < flat.length; i += 2) {
      if (!targetKeys.has(pointKey({ x: flat[i], y: flat[i + 1] }))) continue;
      flat[i] += dx;
      flat[i + 1] += dy;
      changed = true;
    }
    return changed ? { line: flat } : null;
  }
  function compactDefinedRecord(input) {
    const output = {};
    for (const [key, value] of Object.entries(input)) {
      if (value !== void 0) output[key] = value;
    }
    return output;
  }
  function componentKindFromType(componentType) {
    if (componentType === "netflag") return "netflag";
    if (componentType === "netport") return "netport";
    return "component";
  }
  function schematicPrimitiveClassPaths(kind) {
    switch (kind) {
      case "component":
      case "netflag":
      case "netport":
        return COMPONENT_CLASS_PATHS;
      case "wire":
        return WIRE_CLASS_PATHS;
      case "text":
        return TEXT_CLASS_PATHS;
      case "rectangle":
        return RECTANGLE_CLASS_PATHS;
      case "circle":
        return CIRCLE_CLASS_PATHS;
      case "polygon":
        return POLYGON_CLASS_PATHS;
    }
  }
  async function primitiveExistsInClass(primitiveClass, primitiveId) {
    if (typeof primitiveClass.get === "function") {
      try {
        return Boolean(await primitiveClass.get(primitiveId));
      } catch {
        return false;
      }
    }
    if (typeof primitiveClass.getAllPrimitiveId === "function") {
      try {
        return (await primitiveClass.getAllPrimitiveId() || []).includes(primitiveId);
      } catch {
        return false;
      }
    }
    return false;
  }
  function supportsGetAndModify(primitiveClass) {
    return Boolean(primitiveClass) && typeof primitiveClass.get === "function" && typeof primitiveClass.modify === "function";
  }
  function supportsTextModify(primitiveClass) {
    return Boolean(primitiveClass) && typeof primitiveClass.modify === "function" && (typeof primitiveClass.getAll === "function" || typeof primitiveClass.get === "function");
  }
  function componentMoveOrigin(oldX, oldY, property) {
    const changesCoordinate = typeof property.x === "number" || typeof property.y === "number";
    const differsFromCurrent = property.x !== oldX || property.y !== oldY;
    if (typeof oldX === "number" && typeof oldY === "number" && changesCoordinate && differsFromCurrent) {
      return { x: oldX, y: oldY };
    }
    return void 0;
  }
  function createSchematicTransactionOperations(dependencies) {
    const {
      callFirst: callFirst2,
      readFirstPath: readFirstPath2,
      readState: safeGetState2,
      extractPrimitiveId: extractPrimitiveId2,
      readComponentType: readComponentType2,
      readPinPoint: readPinPoint2,
      createBridgeError: newBridgeError2,
      logRecoverableError: logRecoverableError2,
      asPublicTextAlignMode: asPublicTextAlignMode2,
      requirePublicTextAlignMode: requirePublicTextAlignMode2
    } = dependencies;
    const snapshotRecreator = createSchematicSnapshotRecreator({
      callFirst: callFirst2,
      createBridgeError: newBridgeError2,
      requirePublicTextAlignMode: requirePublicTextAlignMode2
    });
    function readTextState(text, key) {
      const publicValue = safeGetState2(text.publicCurrent, key);
      if (publicValue !== void 0) return publicValue;
      return safeGetState2(text.persistentCurrent, key);
    }
    function resolvePublicTextAlignMode(text, primitiveId) {
      const publicAlignMode = asPublicTextAlignMode2(safeGetState2(text.publicCurrent, "AlignMode"));
      if (publicAlignMode !== void 0) {
        dependencies.setCachedTextAlignMode(primitiveId, publicAlignMode);
        return publicAlignMode;
      }
      return dependencies.getCachedTextAlignMode(primitiveId);
    }
    async function applyNetFlagState(current, primitiveId, property) {
      const c = current;
      const applied = {};
      const setIf = (key, setter) => {
        const v = property[key];
        if (v !== void 0 && typeof c[setter] === "function") {
          c[setter](v);
          applied[key] = v;
        }
      };
      setIf("x", "setState_X");
      setIf("y", "setState_Y");
      setIf("rotation", "setState_Rotation");
      setIf("mirror", "setState_Mirror");
      setIf("net", "setState_Net");
      if (typeof c.done === "function") {
        await c.done();
      }
      return { primitiveId, componentType: readComponentType2(current), applied };
    }
    async function readPrimitiveFromClass(paths, primitiveId) {
      for (const path of paths) {
        const primitiveClass = readFirstPath2([path]);
        if (!primitiveClass || typeof primitiveClass.get !== "function") continue;
        try {
          const current = await primitiveClass.get(primitiveId);
          if (current) return { current, className: path };
        } catch (error) {
          logRecoverableError2(`${path}.get(${primitiveId}) failed while creating snapshot`, error);
        }
      }
      return null;
    }
    async function readPublicTextPrimitive(primitiveClass, path, primitiveId) {
      if (typeof primitiveClass.get !== "function") return void 0;
      try {
        return await primitiveClass.get(primitiveId);
      } catch (error) {
        logRecoverableError2(`${path}.get(${primitiveId}) failed while reading text`, error);
        return void 0;
      }
    }
    async function readPersistentTextPrimitive(primitiveClass, path, primitiveId) {
      if (typeof primitiveClass.getAll !== "function") return void 0;
      try {
        const all = await primitiveClass.getAll() || [];
        if (!Array.isArray(all)) return void 0;
        return all.find((item) => extractPrimitiveId2(item) === primitiveId);
      } catch (error) {
        logRecoverableError2(`${path}.getAll() failed while reading text fallback state`, error);
        return void 0;
      }
    }
    function validatedPublicTextPrimitive(publicCurrent, persistentCurrent, primitiveId) {
      if (!publicCurrent) return void 0;
      const publicPrimitiveId = extractPrimitiveId2(publicCurrent);
      const identifiesRequestedPrimitive = publicPrimitiveId === primitiveId;
      const confirmedByInventory = !publicPrimitiveId && Boolean(persistentCurrent);
      return identifiesRequestedPrimitive || confirmedByInventory ? publicCurrent : void 0;
    }
    async function readTextPrimitiveFromClass(paths, primitiveId) {
      for (const path of paths) {
        const primitiveClass = readFirstPath2([path]);
        if (!primitiveClass) continue;
        const persistentCurrent = await readPersistentTextPrimitive(
          primitiveClass,
          path,
          primitiveId
        );
        const publicCandidate = await readPublicTextPrimitive(primitiveClass, path, primitiveId);
        const publicCurrent = validatedPublicTextPrimitive(
          publicCandidate,
          persistentCurrent,
          primitiveId
        );
        if (publicCurrent || persistentCurrent) {
          return { publicCurrent, persistentCurrent, className: path };
        }
      }
      return null;
    }
    function componentSnapshotProperty(current, componentType) {
      if (componentType === "netflag" || componentType === "netport") {
        return compactDefinedRecord({
          x: safeGetState2(current, "X"),
          y: safeGetState2(current, "Y"),
          rotation: safeGetState2(current, "Rotation"),
          mirror: safeGetState2(current, "Mirror"),
          net: safeGetState2(current, "Net")
        });
      }
      return compactDefinedRecord({
        x: safeGetState2(current, "X"),
        y: safeGetState2(current, "Y"),
        rotation: safeGetState2(current, "Rotation"),
        mirror: safeGetState2(current, "Mirror"),
        addIntoBom: safeGetState2(current, "AddIntoBom"),
        addIntoPcb: safeGetState2(current, "AddIntoPcb"),
        designator: safeGetState2(current, "Designator"),
        name: safeGetState2(current, "Name"),
        uniqueId: safeGetState2(current, "UniqueId"),
        manufacturer: safeGetState2(current, "Manufacturer"),
        manufacturerId: safeGetState2(current, "ManufacturerId"),
        supplier: safeGetState2(current, "Supplier"),
        supplierId: safeGetState2(current, "SupplierId"),
        otherProperty: safeGetState2(current, "OtherProperty") || {}
      });
    }
    function componentSnapshot(primitiveId, current) {
      const componentType = readComponentType2(current);
      return {
        schemaVersion: "schematic-primitive-snapshot/v1",
        primitiveId,
        primitiveKind: componentKindFromType(componentType),
        componentType,
        property: componentSnapshotProperty(current, componentType)
      };
    }
    function wireSnapshot(primitiveId, current) {
      return {
        schemaVersion: "schematic-primitive-snapshot/v1",
        primitiveId,
        primitiveKind: "wire",
        property: compactDefinedRecord({
          line: safeGetState2(current, "Line"),
          net: safeGetState2(current, "Net"),
          color: safeGetState2(current, "Color"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType")
        })
      };
    }
    function textSnapshot(primitiveId, text, alignMode) {
      return {
        schemaVersion: "schematic-primitive-snapshot/v1",
        primitiveId,
        primitiveKind: "text",
        property: compactDefinedRecord({
          x: readTextState(text, "X"),
          y: readTextState(text, "Y"),
          content: readTextState(text, "Content"),
          rotation: readTextState(text, "Rotation"),
          color: readTextState(text, "TextColor") ?? readTextState(text, "Color"),
          fontName: readTextState(text, "FontName"),
          fontSize: readTextState(text, "FontSize"),
          bold: readTextState(text, "Bold"),
          italic: readTextState(text, "Italic"),
          underline: readTextState(text, "UnderLine"),
          alignMode
        })
      };
    }
    function rectangleSnapshot(primitiveId, current) {
      return {
        schemaVersion: "schematic-primitive-snapshot/v1",
        primitiveId,
        primitiveKind: "rectangle",
        property: compactDefinedRecord({
          x: safeGetState2(current, "TopLeftX") ?? safeGetState2(current, "X"),
          y: safeGetState2(current, "TopLeftY") ?? safeGetState2(current, "Y"),
          width: safeGetState2(current, "Width"),
          height: safeGetState2(current, "Height"),
          cornerRadius: safeGetState2(current, "CornerRadius"),
          rotation: safeGetState2(current, "Rotation"),
          color: safeGetState2(current, "Color"),
          fillColor: safeGetState2(current, "FillColor"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType"),
          fillStyle: safeGetState2(current, "FillStyle")
        })
      };
    }
    function circleSnapshot(primitiveId, current) {
      return {
        schemaVersion: "schematic-primitive-snapshot/v1",
        primitiveId,
        primitiveKind: "circle",
        property: compactDefinedRecord({
          centerX: safeGetState2(current, "CenterX"),
          centerY: safeGetState2(current, "CenterY"),
          radius: safeGetState2(current, "Radius"),
          color: safeGetState2(current, "Color"),
          fillColor: safeGetState2(current, "FillColor"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType"),
          fillStyle: safeGetState2(current, "FillStyle")
        })
      };
    }
    function polygonSnapshot(primitiveId, current) {
      return {
        schemaVersion: "schematic-primitive-snapshot/v1",
        primitiveId,
        primitiveKind: "polygon",
        property: compactDefinedRecord({
          line: safeGetState2(current, "Line"),
          color: safeGetState2(current, "Color"),
          fillColor: safeGetState2(current, "FillColor"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType")
        })
      };
    }
    async function readComponentSnapshot(primitiveId, expectedKind) {
      const primitive = await readPrimitiveFromClass(COMPONENT_CLASS_PATHS, primitiveId);
      if (!primitive) return null;
      const snapshot = componentSnapshot(primitiveId, primitive.current);
      return expectedKind && snapshot.primitiveKind !== expectedKind ? null : snapshot;
    }
    async function readClassSnapshot(primitiveId, paths, factory) {
      const primitive = await readPrimitiveFromClass(paths, primitiveId);
      return primitive ? factory(primitiveId, primitive.current) : null;
    }
    async function readTextSnapshot(primitiveId) {
      const text = await readTextPrimitiveFromClass(TEXT_CLASS_PATHS, primitiveId);
      if (!text) return { candidateFound: false };
      const alignMode = resolvePublicTextAlignMode(text, primitiveId);
      return {
        candidateFound: true,
        snapshot: alignMode === void 0 ? void 0 : textSnapshot(primitiveId, text, alignMode)
      };
    }
    function throwUnsupportedTextSnapshot(primitiveId) {
      throw newBridgeError2(
        "UNSUPPORTED_RUNTIME",
        `Text ${primitiveId} did not expose a public alignMode`,
        "Retry after reloading the document. Exact text rollback requires a documented ESCH_PrimitiveTextAlignMode value from 1 through 9."
      );
    }
    async function readSnapshotByKind(primitiveId, kind) {
      switch (kind) {
        case "component":
        case "netflag":
        case "netport":
          return readComponentSnapshot(primitiveId, kind);
        case "wire":
          return readClassSnapshot(primitiveId, WIRE_CLASS_PATHS, wireSnapshot);
        case "text": {
          const text = await readTextSnapshot(primitiveId);
          if (text.candidateFound && !text.snapshot) throwUnsupportedTextSnapshot(primitiveId);
          return text.snapshot ?? null;
        }
        case "rectangle":
          return readClassSnapshot(primitiveId, RECTANGLE_CLASS_PATHS, rectangleSnapshot);
        case "circle":
          return readClassSnapshot(primitiveId, CIRCLE_CLASS_PATHS, circleSnapshot);
        case "polygon":
          return readClassSnapshot(primitiveId, POLYGON_CLASS_PATHS, polygonSnapshot);
      }
    }
    async function readUnconstrainedSnapshot(primitiveId) {
      const component = await readComponentSnapshot(primitiveId);
      if (component) return component;
      const wire = await readClassSnapshot(primitiveId, WIRE_CLASS_PATHS, wireSnapshot);
      if (wire) return wire;
      const text = await readTextSnapshot(primitiveId);
      if (text.snapshot) return text.snapshot;
      const rectangle = await readClassSnapshot(
        primitiveId,
        RECTANGLE_CLASS_PATHS,
        rectangleSnapshot
      );
      if (rectangle) return rectangle;
      const circle = await readClassSnapshot(primitiveId, CIRCLE_CLASS_PATHS, circleSnapshot);
      if (circle) return circle;
      const polygon = await readClassSnapshot(primitiveId, POLYGON_CLASS_PATHS, polygonSnapshot);
      if (polygon) return polygon;
      if (text.candidateFound) throwUnsupportedTextSnapshot(primitiveId);
      return null;
    }
    async function getSchematicPrimitiveSnapshot(primitiveId, expectedPrimitiveKind) {
      if (!primitiveId) {
        throw newBridgeError2(
          "INVALID_PARAMS",
          "primitiveId is required",
          "Provide the primitive ID returned by a schematic read or write operation."
        );
      }
      const snapshot = expectedPrimitiveKind ? await readSnapshotByKind(primitiveId, expectedPrimitiveKind) : await readUnconstrainedSnapshot(primitiveId);
      if (snapshot === null) {
        if (expectedPrimitiveKind) {
          throw newBridgeError2(
            "PRIMITIVE_NOT_FOUND",
            `Primitive ${primitiveId} was not found as expected kind ${expectedPrimitiveKind}`,
            "Refresh the expected primitive inventory and retry the transaction."
          );
        }
        throw newBridgeError2(
          "PRIMITIVE_NOT_FOUND",
          `Primitive ${primitiveId} was not found in a transaction-safe schematic class`,
          "Use a component, net flag/port, wire, text, rectangle, circle, or polygon primitive ID."
        );
      }
      return snapshot;
    }
    function parseSchematicPrimitiveSnapshot(input) {
      if (!isRecord2(input)) {
        throw newBridgeError2(
          "INVALID_PARAMS",
          "snapshot must be an object",
          "Pass the exact object returned by schematic.getPrimitiveSnapshot."
        );
      }
      const schemaVersion = input.schemaVersion;
      const primitiveId = input.primitiveId;
      const primitiveKind = input.primitiveKind;
      const property = input.property;
      const allowedKinds = /* @__PURE__ */ new Set([
        "component",
        "netflag",
        "netport",
        "wire",
        "text",
        "rectangle",
        "circle",
        "polygon"
      ]);
      if (schemaVersion !== "schematic-primitive-snapshot/v1" || typeof primitiveId !== "string" || !allowedKinds.has(primitiveKind) || !isRecord2(property)) {
        throw newBridgeError2(
          "INVALID_PARAMS",
          "snapshot does not match schematic-primitive-snapshot/v1",
          "Pass an unmodified snapshot returned by schematic.getPrimitiveSnapshot."
        );
      }
      return {
        schemaVersion,
        primitiveId,
        primitiveKind,
        componentType: typeof input.componentType === "string" ? input.componentType : void 0,
        property: { ...property }
      };
    }
    function parseSchematicPrimitiveKind(value) {
      const allowed = /* @__PURE__ */ new Set([
        "component",
        "netflag",
        "netport",
        "wire",
        "text",
        "rectangle",
        "circle",
        "polygon"
      ]);
      if (typeof value !== "string" || !allowed.has(value)) {
        throw newBridgeError2(
          "INVALID_PARAMS",
          `Unsupported schematic primitive kind: ${String(value)}`,
          `Use one of: ${Array.from(allowed).join(", ")}.`
        );
      }
      return value;
    }
    function primitiveIdFromValue(value) {
      const direct = extractPrimitiveId2(value);
      if (direct) return direct;
      const fallback = safeGetState2(value, "PrimitiveId");
      if (typeof fallback === "string") return fallback;
      if (typeof fallback === "number" || typeof fallback === "bigint") return String(fallback);
      return "";
    }
    async function listSchematicPrimitiveIds(kindInput) {
      const primitiveKind = parseSchematicPrimitiveKind(kindInput);
      const primitiveClass = readFirstPath2(schematicPrimitiveClassPaths(primitiveKind));
      if (!primitiveClass) return { primitiveKind, primitiveIds: [] };
      let values = [];
      if (typeof primitiveClass.getAll === "function") {
        try {
          values = primitiveKind === "component" || primitiveKind === "netflag" || primitiveKind === "netport" ? await primitiveClass.getAll(void 0, true) || [] : await primitiveClass.getAll() || [];
        } catch (error) {
          logRecoverableError2(`failed to list ${primitiveKind} primitives`, error);
        }
      }
      if (values.length === 0 && typeof primitiveClass.getAllPrimitiveId === "function") {
        try {
          const primitiveIds2 = (await primitiveClass.getAllPrimitiveId() || []).filter(
            (value) => typeof value === "string" && value.length > 0
          ).sort((a, b) => a.localeCompare(b));
          return { primitiveKind, primitiveIds: Array.from(new Set(primitiveIds2)) };
        } catch (error) {
          logRecoverableError2(`failed to list ${primitiveKind} primitive IDs`, error);
        }
      }
      const primitiveIds = values.filter((value) => {
        if (primitiveKind === "component") {
          const componentType = readComponentType2(value);
          return componentType !== "netflag" && componentType !== "netport";
        }
        if (primitiveKind === "netflag" || primitiveKind === "netport") {
          return readComponentType2(value) === primitiveKind;
        }
        return true;
      }).map(primitiveIdFromValue).filter(Boolean).sort((a, b) => a.localeCompare(b));
      return { primitiveKind, primitiveIds: Array.from(new Set(primitiveIds)) };
    }
    async function deleteSchematicPrimitives(primitiveIdsInput) {
      const primitiveIds = Array.isArray(primitiveIdsInput) ? primitiveIdsInput.filter(
        (value) => typeof value === "string" && value.length > 0
      ) : [];
      const kinds = [
        "component",
        "wire",
        "text",
        "rectangle",
        "circle",
        "polygon"
      ];
      const deleted = [];
      const notFound = [];
      for (const primitiveId of primitiveIds) {
        let owner;
        for (const kind of kinds) {
          const primitiveClass = readFirstPath2(schematicPrimitiveClassPaths(kind));
          if (!primitiveClass || typeof primitiveClass.delete !== "function") continue;
          if (await primitiveExistsInClass(primitiveClass, primitiveId)) {
            owner = primitiveClass;
            break;
          }
        }
        if (!owner) {
          notFound.push(primitiveId);
          continue;
        }
        await owner.delete([primitiveId]);
        dependencies.deleteCachedTextAlignMode(primitiveId);
        deleted.push(primitiveId);
      }
      return { success: notFound.length === 0, deleted, notFound };
    }
    async function recreateSchematicPrimitiveSnapshot(input) {
      const snapshot = parseSchematicPrimitiveSnapshot(input);
      const before = new Set((await listSchematicPrimitiveIds(snapshot.primitiveKind)).primitiveIds);
      const result = await snapshotRecreator.create(snapshot);
      let primitiveId = extractPrimitiveId2(result);
      if (!primitiveId) {
        const after = (await listSchematicPrimitiveIds(snapshot.primitiveKind)).primitiveIds;
        const added = after.filter((id) => !before.has(id));
        if (added.length === 1) primitiveId = added[0];
      }
      if (!primitiveId) {
        throw newBridgeError2(
          "CREATE_UNCONFIRMED",
          `Recreated ${snapshot.primitiveKind} did not expose a unique primitive ID`,
          "Inspect the sheet before retrying; the primitive may have been created without an addressable result."
        );
      }
      return { primitiveId, snapshot: await getSchematicPrimitiveSnapshot(primitiveId) };
    }
    async function getComponentPinCoordinates(primitiveId) {
      let pins;
      try {
        pins = await callFirst2(
          [
            "SCH_PrimitiveComponent.getAllPinsByPrimitiveId",
            "sch_PrimitiveComponent.getAllPinsByPrimitiveId"
          ],
          primitiveId
        );
      } catch (e) {
        logRecoverableError2(`failed to read pins for ${primitiveId}`, e);
        return [];
      }
      const pinList = Array.isArray(pins) ? pins : [];
      const points = [];
      for (const pin of pinList) {
        const point = readPinPoint2(pin);
        if (typeof point.x === "number" && typeof point.y === "number") {
          points.push({ x: point.x, y: point.y });
        }
      }
      return points;
    }
    async function followConnectedWires(oldPinPoints, dx, dy) {
      const outcome = { movedWireIds: [], failedWireIds: [] };
      const schWireClass = readFirstPath2(["SCH_PrimitiveWire", "sch_PrimitiveWire"]);
      if (!schWireClass || typeof schWireClass.getAll !== "function" || typeof schWireClass.modify !== "function") {
        return outcome;
      }
      const targetKeys = new Set(oldPinPoints.map((p) => pointKey(p)));
      let wires;
      try {
        wires = await schWireClass.getAll() || [];
      } catch (e) {
        logRecoverableError2("failed to read wires while following a component move", e);
        return outcome;
      }
      for (const wire of wires) {
        const shifted = shiftWireLine(safeGetState2(wire, "Line"), targetKeys, dx, dy);
        if (!shifted) continue;
        const wireId = extractPrimitiveId2(wire);
        if (!wireId) {
          outcome.failedWireIds.push("<unknown>");
          continue;
        }
        try {
          await schWireClass.modify(wireId, {
            line: shifted.line,
            net: safeGetState2(wire, "Net"),
            color: safeGetState2(wire, "Color"),
            lineWidth: safeGetState2(wire, "LineWidth"),
            lineType: safeGetState2(wire, "LineType")
          });
          outcome.movedWireIds.push(wireId);
        } catch (e) {
          logRecoverableError2(`failed to follow wire ${wireId} after component move`, e);
          outcome.failedWireIds.push(wireId);
        }
      }
      return outcome;
    }
    async function readModificationCurrent(primitiveClass, primitiveId, className) {
      try {
        return await primitiveClass.get(primitiveId);
      } catch (error) {
        logRecoverableError2(`${className}.get(${primitiveId}) failed`, error);
        return void 0;
      }
    }
    function componentModificationProperties(current, property) {
      const existingOther = safeGetState2(current, "OtherProperty") || {};
      const incomingOther = property.otherProperty;
      const oldX = safeGetState2(current, "X");
      const oldY = safeGetState2(current, "Y");
      return {
        oldX,
        oldY,
        merged: {
          x: oldX,
          y: oldY,
          rotation: safeGetState2(current, "Rotation"),
          mirror: safeGetState2(current, "Mirror"),
          addIntoBom: safeGetState2(current, "AddIntoBom"),
          addIntoPcb: safeGetState2(current, "AddIntoPcb"),
          designator: safeGetState2(current, "Designator"),
          name: safeGetState2(current, "Name"),
          uniqueId: safeGetState2(current, "UniqueId"),
          manufacturer: safeGetState2(current, "Manufacturer"),
          manufacturerId: safeGetState2(current, "ManufacturerId"),
          supplier: safeGetState2(current, "Supplier"),
          supplierId: safeGetState2(current, "SupplierId"),
          ...property,
          otherProperty: incomingOther ? { ...existingOther, ...incomingOther } : existingOther
        }
      };
    }
    async function tryModifyComponent(primitiveId, property) {
      const primitiveClass = readFirstPath2(COMPONENT_CLASS_PATHS);
      if (!supportsGetAndModify(primitiveClass)) return NOT_HANDLED;
      const current = await readModificationCurrent(
        primitiveClass,
        primitiveId,
        "SCH_PrimitiveComponent"
      );
      if (!current) return NOT_HANDLED;
      const componentType = readComponentType2(current);
      if (componentType === "netflag" || componentType === "netport") {
        return handled(await applyNetFlagState(current, primitiveId, property));
      }
      const { merged, oldX, oldY } = componentModificationProperties(current, property);
      const moveOrigin = componentMoveOrigin(oldX, oldY, property);
      const oldPinPoints = moveOrigin ? await getComponentPinCoordinates(primitiveId) : [];
      const result = await primitiveClass.modify(primitiveId, merged);
      const followResult = { movedWireIds: [], failedWireIds: [] };
      if (moveOrigin && oldPinPoints.length > 0) {
        const dx = merged.x - moveOrigin.x;
        const dy = merged.y - moveOrigin.y;
        Object.assign(followResult, await followConnectedWires(oldPinPoints, dx, dy));
      }
      return handled({
        result,
        followedWireIds: followResult.movedWireIds,
        wireFollowFailures: followResult.failedWireIds
      });
    }
    async function tryModifyWire(primitiveId, property) {
      const primitiveClass = readFirstPath2(WIRE_CLASS_PATHS);
      if (!supportsGetAndModify(primitiveClass)) return NOT_HANDLED;
      const current = await readModificationCurrent(primitiveClass, primitiveId, "SCH_PrimitiveWire");
      if (!current) return NOT_HANDLED;
      return handled(
        await primitiveClass.modify(primitiveId, {
          line: safeGetState2(current, "Line"),
          net: safeGetState2(current, "Net"),
          color: safeGetState2(current, "Color"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType"),
          ...property
        })
      );
    }
    function textModificationProperties(text, property, alignMode) {
      const incoming = { ...property };
      if (incoming.color !== void 0) incoming.textColor = incoming.color;
      if (incoming.underline !== void 0) incoming.underLine = incoming.underline;
      delete incoming.color;
      delete incoming.underline;
      incoming.alignMode = alignMode;
      return {
        x: readTextState(text, "X"),
        y: readTextState(text, "Y"),
        content: readTextState(text, "Content"),
        rotation: readTextState(text, "Rotation"),
        textColor: readTextState(text, "TextColor") ?? readTextState(text, "Color"),
        fontName: readTextState(text, "FontName"),
        fontSize: readTextState(text, "FontSize"),
        bold: readTextState(text, "Bold"),
        italic: readTextState(text, "Italic"),
        underLine: readTextState(text, "UnderLine"),
        ...incoming
      };
    }
    async function tryModifyText(primitiveId, property) {
      const primitiveClass = readFirstPath2(TEXT_CLASS_PATHS);
      if (!supportsTextModify(primitiveClass)) return NOT_HANDLED;
      const text = await readTextPrimitiveFromClass(TEXT_CLASS_PATHS, primitiveId);
      if (!text) return NOT_HANDLED;
      let requestedAlignMode;
      if (Object.prototype.hasOwnProperty.call(property, "alignMode")) {
        requestedAlignMode = requirePublicTextAlignMode2(property.alignMode);
      }
      const alignMode = requestedAlignMode ?? resolvePublicTextAlignMode(text, primitiveId);
      if (alignMode === void 0) {
        throw newBridgeError2(
          "UNSUPPORTED_RUNTIME",
          `Text ${primitiveId} did not expose a public alignMode`,
          "Read the text after reloading the document, or provide alignMode explicitly using a value from 1 through 9."
        );
      }
      const result = await primitiveClass.modify(
        primitiveId,
        textModificationProperties(text, property, alignMode)
      );
      const resultAlignMode = asPublicTextAlignMode2(safeGetState2(result, "AlignMode"));
      dependencies.setCachedTextAlignMode(primitiveId, resultAlignMode ?? alignMode);
      return handled(result);
    }
    async function tryModifyCircle(primitiveId, property) {
      const primitiveClass = readFirstPath2(CIRCLE_CLASS_PATHS);
      if (!supportsGetAndModify(primitiveClass)) return NOT_HANDLED;
      const current = await readModificationCurrent(
        primitiveClass,
        primitiveId,
        "SCH_PrimitiveCircle"
      );
      if (!current) return NOT_HANDLED;
      return handled(
        await primitiveClass.modify(primitiveId, {
          centerX: safeGetState2(current, "CenterX"),
          centerY: safeGetState2(current, "CenterY"),
          radius: safeGetState2(current, "Radius"),
          color: safeGetState2(current, "Color"),
          fillColor: safeGetState2(current, "FillColor"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType"),
          fillStyle: safeGetState2(current, "FillStyle"),
          ...property
        })
      );
    }
    async function tryModifyPolygon(primitiveId, property) {
      const primitiveClass = readFirstPath2(POLYGON_CLASS_PATHS);
      if (!supportsGetAndModify(primitiveClass)) return NOT_HANDLED;
      const current = await readModificationCurrent(
        primitiveClass,
        primitiveId,
        "SCH_PrimitivePolygon"
      );
      if (!current) return NOT_HANDLED;
      return handled(
        await primitiveClass.modify(primitiveId, {
          line: safeGetState2(current, "Line"),
          color: safeGetState2(current, "Color"),
          fillColor: safeGetState2(current, "FillColor"),
          lineWidth: safeGetState2(current, "LineWidth"),
          lineType: safeGetState2(current, "LineType"),
          ...property
        })
      );
    }
    async function modifyPrimitive(primitiveId, property) {
      const handlers = [
        tryModifyComponent,
        tryModifyWire,
        tryModifyText,
        tryModifyCircle,
        tryModifyPolygon
      ];
      for (const handler of handlers) {
        const attempt = await handler(primitiveId, property);
        if (attempt.handled) return attempt.value;
      }
      return callFirst2(
        [
          "SCH_PrimitiveComponent.modify",
          "SCH_PrimitiveWire.modify",
          "sch_PrimitiveComponent.modify",
          "sch_PrimitiveWire.modify"
        ],
        primitiveId,
        property
      );
    }
    async function restorePrimitiveSnapshot(input) {
      const snapshot = parseSchematicPrimitiveSnapshot(input);
      await modifyPrimitive(snapshot.primitiveId, snapshot.property);
      return {
        restored: true,
        snapshot: await getSchematicPrimitiveSnapshot(snapshot.primitiveId)
      };
    }
    return {
      getPrimitiveSnapshot: getSchematicPrimitiveSnapshot,
      listPrimitiveIds: listSchematicPrimitiveIds,
      deletePrimitives: deleteSchematicPrimitives,
      recreatePrimitiveSnapshot: recreateSchematicPrimitiveSnapshot,
      restorePrimitiveSnapshot,
      modifyPrimitive
    };
  }

  // src/dispatcher.ts
  var BUILD_ID = "dce89x353cx43ac" ? "dce89x353cx43ac" : "baked-dev";
  var METHOD_LIST = [
    "api.call",
    "api.execute",
    "board.exportGerbers",
    "board.getDimensions",
    "board.getFeatures",
    "board.getStackup",
    "board.listLayers",
    "bom.generate",
    "bom.validate",
    "canvas.capture",
    "canvas.captureRegion",
    "canvas.locate",
    "design.drc",
    "design.erc",
    "design.ruleCheck",
    "export.netlist",
    "export.pdf",
    "export.pickPlace",
    "inventory.getPrice",
    "inventory.search",
    "library.getDeviceByLcscId",
    "pcb.addSilkscreenLine",
    "pcb.addText",
    "pcb.addTrack",
    "pcb.addVia",
    "pcb.addZone",
    "pcb.deleteComponent",
    "pcb.exportRouteContext",
    "pcb.listComponents",
    "pcb.listFills",
    "pcb.listRegions",
    "pcb.listTracks",
    "pcb.listVias",
    "pcb.modifyComponent",
    "pcb.rebuildCopper",
    "project.export",
    "project.open",
    "project.save",
    "schematic.addCircle",
    "schematic.addPolygon",
    "schematic.addRectangle",
    "schematic.addText",
    "schematic.addWire",
    "schematic.connectPinToNet",
    "schematic.connectPinsByNet",
    "schematic.createNetFlag",
    "schematic.createNetPort",
    "schematic.deletePrimitive",
    "schematic.getNetDetail",
    "schematic.getPinNoConnect",
    "schematic.getPrimitiveSnapshot",
    "schematic.getSheetInfo",
    "schematic.listComponents",
    "schematic.listNets",
    "schematic.listPrimitiveIds",
    "schematic.listRectangles",
    "schematic.modifyPrimitive",
    "schematic.placeComponent",
    "schematic.primitiveBounds",
    "schematic.recreatePrimitiveSnapshot",
    "schematic.restorePrimitiveSnapshot",
    "schematic.searchDevice",
    "schematic.setPinNoConnect",
    "schematic.setTitleBlock",
    "schematic.syncToPcb",
    "schematic.validateNetlist",
    "system.apiInventory",
    "system.getStatus",
    "system.inspectComponents",
    "system.inspectWires"
  ];
  var callFirst;
  var readFirstPath;
  var inspectApiInventory;
  var callAllowedApi;
  var boardInspection;
  var canvasOperations;
  var designRuleCheckOperations;
  var domainRouter;
  var exportOperations;
  var pcbMutationOperations;
  var pcbReadOperations;
  var pcbWriteOperations;
  var projectOperations;
  var readOnlyOperations;
  var schematicComponentInspection;
  var schematicInspection;
  var schematicTransactionOperations;
  var systemApiOperations;
  function newBridgeError(code, message, suggestion, data) {
    const error = new Error(message);
    Object.assign(error, { code, suggestion, data });
    return error;
  }
  function nativeScalarString3(value) {
    return typeof value === "string" || typeof value === "number" || typeof value === "boolean" || typeof value === "bigint" ? String(value) : "";
  }
  async function needDevice(v) {
    const d = v;
    const u = nativeScalarString3(d?.uuid).trim();
    const l = nativeScalarString3(d?.libraryUuid).trim();
    if (u && l && await callFirst(["LIB_Device.get"], u, l)) return;
    throw newBridgeError("INVALID_PARAMS", "Invalid device.", "Use search_device.");
  }
  function extractPrimitiveId(result) {
    if (!result || typeof result !== "object") return "";
    const obj = result;
    const direct = nativeScalarString3(obj.primitiveId ?? obj.uuid);
    if (direct) return direct;
    try {
      const getter = obj.getState_PrimitiveId;
      if (typeof getter === "function") {
        const id = nativeScalarString3(getter.call(obj));
        if (id) return id;
      }
    } catch {
    }
    try {
      const getState = obj.getState;
      if (typeof getState === "function") {
        const state = getState.call(obj);
        const id = nativeScalarString3(state?.PrimitiveId);
        if (id) return id;
      }
    } catch {
    }
    return "";
  }
  function callStateGetter(obj, record, key) {
    const getter = record[`getState_${key}`];
    if (typeof getter !== "function") return void 0;
    try {
      return getter.call(obj);
    } catch {
      return void 0;
    }
  }
  function readStateObject(obj, record, key, lowerCamelKey) {
    if (typeof record.getState !== "function") return void 0;
    try {
      const state = record.getState.call(obj);
      if (!isRecord2(state)) return void 0;
      if (key in state) return state[key];
      if (lowerCamelKey in state) return state[lowerCamelKey];
    } catch {
      return void 0;
    }
    return void 0;
  }
  function safeGetState(obj, key) {
    if (!isRecord2(obj)) return void 0;
    const lowerCamelKey = key.length > 0 ? key.charAt(0).toLowerCase() + key.slice(1) : key;
    const getterValue = callStateGetter(obj, obj, key);
    if (getterValue !== void 0) return getterValue;
    const stateValue = readStateObject(obj, obj, key, lowerCamelKey);
    if (stateValue !== void 0) return stateValue;
    if (key in obj) return obj[key];
    return obj[lowerCamelKey];
  }
  var textAlignModeCache = /* @__PURE__ */ new Map();
  function asPublicTextAlignMode(value) {
    return typeof value === "number" && Number.isInteger(value) && value >= 1 && value <= 9 ? value : void 0;
  }
  function requirePublicTextAlignMode(value, field = "alignMode") {
    const alignMode = asPublicTextAlignMode(value);
    if (alignMode === void 0) {
      throw newBridgeError(
        "INVALID_PARAMS",
        `${field} must be an integer from 1 through 9`,
        "Use the documented ESCH_PrimitiveTextAlignMode values: LEFT_TOP=1 through RIGHT_BOTTOM=9."
      );
    }
    return alignMode;
  }
  function normalizeWireLine(line) {
    if (!Array.isArray(line) || line.length === 0) return [];
    if (Array.isArray(line[0])) {
      return line.filter((pair) => Array.isArray(pair) && pair.length >= 2).map(([x, y]) => ({ x, y }));
    }
    const flat = line;
    const pts = [];
    for (let i = 0; i + 1 < flat.length; i += 2) {
      pts.push({ x: flat[i], y: flat[i + 1] });
    }
    return pts;
  }
  function isBetween(value, a, b) {
    return value >= Math.min(a, b) && value <= Math.max(a, b);
  }
  function samePoint(a, b) {
    return a.x === b.x && a.y === b.y;
  }
  function pointOnAxisAlignedSegment(point, a, b) {
    if (a.x === b.x) return point.x === a.x && isBetween(point.y, a.y, b.y);
    if (a.y === b.y) return point.y === a.y && isBetween(point.x, a.x, b.x);
    return samePoint(point, a) || samePoint(point, b);
  }
  function pointOnPolyline(point, points) {
    if (points.length === 1) return samePoint(point, points[0]);
    for (let i = 0; i + 1 < points.length; i += 1) {
      if (pointOnAxisAlignedSegment(point, points[i], points[i + 1])) return true;
    }
    return false;
  }
  function axisAlignedSegmentIntersection(a1, a2, b1, b2) {
    const aVertical = a1.x === a2.x;
    const aHorizontal = a1.y === a2.y;
    const bVertical = b1.x === b2.x;
    const bHorizontal = b1.y === b2.y;
    if (aVertical && bVertical && a1.x === b1.x) {
      const y = Math.max(Math.min(a1.y, a2.y), Math.min(b1.y, b2.y));
      if (isBetween(y, a1.y, a2.y) && isBetween(y, b1.y, b2.y)) return { x: a1.x, y };
    }
    if (aHorizontal && bHorizontal && a1.y === b1.y) {
      const x = Math.max(Math.min(a1.x, a2.x), Math.min(b1.x, b2.x));
      if (isBetween(x, a1.x, a2.x) && isBetween(x, b1.x, b2.x)) return { x, y: a1.y };
    }
    if (aVertical && bHorizontal && isBetween(a1.x, b1.x, b2.x) && isBetween(b1.y, a1.y, a2.y)) {
      return { x: a1.x, y: b1.y };
    }
    if (aHorizontal && bVertical && isBetween(b1.x, a1.x, a2.x) && isBetween(a1.y, b1.y, b2.y)) {
      return { x: b1.x, y: a1.y };
    }
    return null;
  }
  function polylineIntersection(a, b) {
    for (let i = 0; i + 1 < a.length; i += 1) {
      for (let j = 0; j + 1 < b.length; j += 1) {
        const intersection = axisAlignedSegmentIntersection(a[i], a[i + 1], b[j], b[j + 1]);
        if (intersection) return intersection;
      }
    }
    return null;
  }
  function parsePointKey(key) {
    const [xRaw, yRaw] = key.split(",");
    const x = Number(xRaw);
    const y = Number(yRaw);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return { x, y };
  }
  async function collectPinCoordinateNets() {
    const coordToNet = /* @__PURE__ */ new Map();
    try {
      const netlistData = await listNetsApi();
      for (const net of netlistData) {
        for (const node of net.nodes) {
          if (typeof node.x === "number" && typeof node.y === "number") {
            coordToNet.set(pointKey2({ x: node.x, y: node.y }), net.netName);
          }
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      if (!message.includes("SCH_PrimitiveComponent class not found")) {
        logRecoverableError("failed to build pin coordinate map for net-collision check", e);
      }
    }
    return coordToNet;
  }
  async function collectFlagPortCoordinateNets() {
    const coordToNet = /* @__PURE__ */ new Map();
    const schCompClass = readFirstPath([
      "SCH_PrimitiveComponent",
      "SCH_PrimitiveComponent3",
      "sch_PrimitiveComponent"
    ]);
    if (!schCompClass || typeof schCompClass.getAll !== "function") return coordToNet;
    try {
      const allComps = await schCompClass.getAll(void 0, true) || [];
      for (const c of allComps) {
        const type = readComponentType(c);
        if (type !== "netflag" && type !== "netport") continue;
        const netName = readComponentNet(c);
        const point = readPrimitivePoint(c);
        if (netName && point) coordToNet.set(pointKey2(point), netName);
      }
    } catch (e) {
      logRecoverableError("failed to read net flags/ports for net-collision check", e);
    }
    return coordToNet;
  }
  async function buildForeignConnectivityMap() {
    const [pinCoords, flagCoords] = await Promise.all([
      collectPinCoordinateNets(),
      collectFlagPortCoordinateNets()
    ]);
    return new Map([...pinCoords, ...flagCoords]);
  }
  async function shouldSuppressDuplicateWireNetName(points, netName) {
    if (!netName || points.length === 0) return false;
    const pointKeys = new Set(points.map(pointKey2));
    const schWireClass = readFirstPath(["SCH_PrimitiveWire", "sch_PrimitiveWire"]);
    if (schWireClass && typeof schWireClass.getAll === "function") {
      try {
        const wires = await schWireClass.getAll() || [];
        for (const wire of wires) {
          const wireNet = String(safeGetState(wire, "Net") ?? "");
          if (wireNet !== netName) continue;
          for (const point of normalizeWireLine(safeGetState(wire, "Line"))) {
            if (pointKeys.has(pointKey2(point))) return true;
          }
        }
      } catch (e) {
        logRecoverableError("failed to read existing wires for duplicate-net-label suppression", e);
      }
    }
    const connectivityMap = await buildForeignConnectivityMap();
    for (const point of points) {
      if (connectivityMap.get(pointKey2(point)) === netName) return true;
    }
    return false;
  }
  async function findForeignNetCollision(points, netName) {
    if (!netName || points.length === 0) return null;
    const schWireClass = readFirstPath(["SCH_PrimitiveWire", "sch_PrimitiveWire"]);
    if (schWireClass && typeof schWireClass.getAll === "function") {
      let wires;
      try {
        wires = await schWireClass.getAll() || [];
      } catch (e) {
        logRecoverableError("failed to read existing wires for net-collision check", e);
        wires = [];
      }
      for (const wire of wires) {
        const wireNet = String(safeGetState(wire, "Net") ?? "");
        if (!wireNet || wireNet === netName) continue;
        const wirePts = normalizeWireLine(safeGetState(wire, "Line"));
        const intersection = polylineIntersection(points, wirePts);
        if (intersection) {
          return { x: intersection.x, y: intersection.y, foreignNet: wireNet, kind: "wire" };
        }
      }
    }
    const foreignMap = await buildForeignConnectivityMap();
    for (const [key, foreignNet] of foreignMap) {
      const p = parsePointKey(key);
      if (!p) continue;
      if (foreignNet && foreignNet !== netName) {
        if (pointOnPolyline(p, points)) {
          return { x: p.x, y: p.y, foreignNet, kind: "pin_or_flag" };
        }
      }
    }
    return null;
  }
  function summarizeWirePrimitive(wire) {
    const normalized = normalizeStandalone(wire, 4);
    const output = isRecord2(normalized) ? { ...normalized } : { value: normalized };
    const state = compactPrimitiveSummary(wire, [
      "PrimitiveType",
      "PrimitiveId",
      "Line",
      "Net",
      "Color",
      "LineWidth",
      "LineType"
    ]);
    output.primitiveType = state.PrimitiveType ?? output.primitiveType ?? "";
    output.primitiveId = state.PrimitiveId ?? output.primitiveId ?? "";
    output.line = state.Line ?? output.line ?? null;
    output.net = state.Net ?? output.net ?? "";
    output.color = state.Color ?? output.color ?? null;
    output.lineWidth = state.LineWidth ?? output.lineWidth ?? null;
    output.lineType = state.LineType ?? output.lineType ?? null;
    output.state = state;
    return output;
  }
  var NET_DETAIL_DEFAULT_TIMEOUT_MS = 15e3;
  var NET_DETAIL_MAX_TIMEOUT_MS = 2e4;
  var NET_DETAIL_STAGE_TIMEOUT_MS = 5e3;
  function createNetDetailBudget(netName, requestedTimeoutMs) {
    const numericTimeout = typeof requestedTimeoutMs === "number" && Number.isFinite(requestedTimeoutMs) ? Math.trunc(requestedTimeoutMs) : NET_DETAIL_DEFAULT_TIMEOUT_MS;
    const operationTimeoutMs = Math.max(1, Math.min(NET_DETAIL_MAX_TIMEOUT_MS, numericTimeout));
    const startedAt = Date.now();
    return {
      netName,
      startedAt,
      deadlineAt: startedAt + operationTimeoutMs,
      operationTimeoutMs
    };
  }
  function isNetDetailTimeout(error) {
    return isRecord2(error) && error.code === "NET_DETAIL_TIMEOUT";
  }
  async function awaitNetDetailStage(budget, stage, operation, context = {}) {
    if (!budget) return await operation();
    const remainingMs = budget.deadlineAt - Date.now();
    const stageTimeoutMs = Math.min(NET_DETAIL_STAGE_TIMEOUT_MS, remainingMs);
    if (stageTimeoutMs <= 0) {
      throw newBridgeError(
        "NET_DETAIL_TIMEOUT",
        `Net detail scan timed out before ${stage} while resolving "${budget.netName}".`,
        "Retry with the affected schematic focused; inspect the timeout stage and component in error data.",
        {
          stage,
          netName: budget.netName,
          elapsedMs: Date.now() - budget.startedAt,
          operationTimeoutMs: budget.operationTimeoutMs,
          ...context
        }
      );
    }
    let timer;
    try {
      return await Promise.race([
        Promise.resolve().then(operation),
        new Promise((_resolve, reject) => {
          timer = setTimeout(() => {
            reject(
              newBridgeError(
                "NET_DETAIL_TIMEOUT",
                `Net detail scan timed out during ${stage} while resolving "${budget.netName}".`,
                "Retry with the affected schematic focused; inspect the timeout stage and component in error data.",
                {
                  stage,
                  netName: budget.netName,
                  elapsedMs: Date.now() - budget.startedAt,
                  operationTimeoutMs: budget.operationTimeoutMs,
                  stageTimeoutMs,
                  ...context
                }
              )
            );
          }, stageTimeoutMs);
        })
      ]);
    } finally {
      if (timer !== void 0) clearTimeout(timer);
    }
  }
  function createDisjointSet() {
    const parent = /* @__PURE__ */ new Map();
    const find = (key) => {
      if (!parent.has(key)) parent.set(key, key);
      const currentParent = parent.get(key);
      if (!currentParent || currentParent === key) return key;
      const root = find(currentParent);
      parent.set(key, root);
      return root;
    };
    return {
      parent,
      find,
      union: (a, b) => {
        const rootA = find(a);
        const rootB = find(b);
        if (rootA !== rootB) parent.set(rootB, rootA);
      }
    };
  }
  function pointKey2(point) {
    return `${Math.round(point.x * 1e3) / 1e3},${Math.round(point.y * 1e3) / 1e3}`;
  }
  function parseLinePoints(line) {
    if (!Array.isArray(line)) return [];
    const segments = line.every((item) => typeof item === "number") ? [line] : line;
    const points = [];
    for (const item of segments) {
      if (!Array.isArray(item) || item.length < 2) continue;
      for (let i = 0; i + 1 < item.length; i += 2) {
        const x = Number(item[i]);
        const y = Number(item[i + 1]);
        if (Number.isFinite(x) && Number.isFinite(y)) points.push({ x, y });
      }
    }
    return points;
  }
  function readStringMemberOrState(source, key, stateName) {
    const stateValue = readStateValue(source, stateName, 2);
    if (typeof stateValue === "string" && stateValue) return stateValue;
    const directValue = readMember(source, key);
    if (typeof directValue === "string") return directValue;
    if (typeof directValue === "number") return String(directValue);
    return "";
  }
  function readNumberMemberOrState(source, key, stateName) {
    const stateValue = readStateValue(source, stateName, 2);
    if (typeof stateValue === "number" && Number.isFinite(stateValue)) return stateValue;
    const directValue = readMember(source, key);
    if (typeof directValue === "number" && Number.isFinite(directValue)) return directValue;
    return void 0;
  }
  function ensureNetEntry(netMap, netName) {
    const existing = netMap.get(netName);
    if (existing) return existing;
    const nodes = [];
    netMap.set(netName, nodes);
    return nodes;
  }
  function pushUniqueNetNode(netMap, netName, node) {
    if (!netName || !node.component || !node.pin) return;
    const nodes = ensureNetEntry(netMap, netName);
    if (nodes.some((item) => item.component === node.component && item.pin === node.pin)) return;
    nodes.push(node);
  }
  function readComponentType(component) {
    return readStringMemberOrState(component, "componentType", "ComponentType").toLowerCase();
  }
  function readComponentNet(component) {
    const directNet = readStringMemberOrState(component, "net", "Net");
    if (directNet) return directNet;
    const otherProperty = readMember(component, "otherProperty");
    if (isRecord2(otherProperty)) {
      return String(otherProperty.net ?? otherProperty.Net ?? "");
    }
    return "";
  }
  function readPrimitivePoint(source) {
    const x = readNumberMemberOrState(source, "x", "X");
    const y = readNumberMemberOrState(source, "y", "Y");
    if (x === void 0 || y === void 0) return void 0;
    return { x, y };
  }
  function addUnnamedWireNetLabels(netMap, dsu, rootNetNames) {
    const canonicalPointByRoot = /* @__PURE__ */ new Map();
    for (const point of dsu.parent.keys()) {
      const root = dsu.find(point);
      const canonicalPoint = canonicalPointByRoot.get(root);
      if (!canonicalPoint || point.localeCompare(canonicalPoint) < 0) {
        canonicalPointByRoot.set(root, point);
      }
    }
    const unnamedRoots = Array.from(canonicalPointByRoot.entries()).filter(([root]) => !rootNetNames.get(root)?.size).sort((a, b) => a[1].localeCompare(b[1]));
    let nextAnonymousNet = 1;
    for (const [root] of unnamedRoots) {
      let netName = `N$${nextAnonymousNet}`;
      while (netMap.has(netName)) {
        nextAnonymousNet += 1;
        netName = `N$${nextAnonymousNet}`;
      }
      nextAnonymousNet += 1;
      rootNetNames.set(root, /* @__PURE__ */ new Set([netName]));
      ensureNetEntry(netMap, netName);
    }
  }
  async function addCoordinateFallbackNets(netMap, comps, budget) {
    const schWireClass = readFirstPath([
      "SCH_PrimitiveWire",
      "SCH_PrimitiveWire3",
      "sch_PrimitiveWire"
    ]);
    if (!schWireClass || typeof schWireClass.getAll !== "function") return false;
    const wires = await awaitNetDetailStage(budget, "wire_read", () => schWireClass.getAll());
    if (!Array.isArray(wires)) return false;
    const wireItems = wires;
    const dsu = createDisjointSet();
    const rootNetNames = /* @__PURE__ */ new Map();
    const addNetLabel = (point, netName) => {
      if (!netName) return;
      const root = dsu.find(pointKey2(point));
      const names = rootNetNames.get(root) ?? /* @__PURE__ */ new Set();
      names.add(netName);
      rootNetNames.set(root, names);
      ensureNetEntry(netMap, netName);
    };
    for (const wire of wireItems) {
      const wireSummary = summarizeWirePrimitive(wire);
      const points = parseLinePoints(wireSummary.line);
      if (points.length === 0) continue;
      for (const point of points) dsu.find(pointKey2(point));
      for (let i = 1; i < points.length; i += 1) {
        dsu.union(pointKey2(points[i - 1]), pointKey2(points[i]));
      }
      const netName = typeof wireSummary.net === "string" ? wireSummary.net : "";
      if (netName) addNetLabel(points[0], netName);
    }
    for (const [root, names] of Array.from(rootNetNames.entries())) {
      const normalizedRoot = dsu.find(root);
      if (normalizedRoot === root) continue;
      const target = rootNetNames.get(normalizedRoot) ?? /* @__PURE__ */ new Set();
      for (const name of names) target.add(name);
      rootNetNames.set(normalizedRoot, target);
      rootNetNames.delete(root);
    }
    for (const component of comps) {
      const componentType = readComponentType(component);
      if (componentType !== "netflag" && componentType !== "netport") continue;
      const netName = readComponentNet(component);
      const point = readPrimitivePoint(component);
      if (!netName || !point) continue;
      addNetLabel(point, netName);
    }
    addUnnamedWireNetLabels(netMap, dsu, rootNetNames);
    for (const component of comps) {
      const ref = readStringMemberOrState(component, "designator", "Designator");
      if (!ref || typeof component.getAllPins !== "function") continue;
      try {
        const pins = await awaitNetDetailStage(
          budget,
          "coordinate_pin_read",
          () => component.getAllPins(),
          { component: ref }
        );
        for (const pin of pins || []) {
          const pinNumber = readStringMemberOrState(pin, "pinNumber", "PinNumber");
          const point = readPrimitivePoint(pin);
          if (!pinNumber || !point) continue;
          const netNames = rootNetNames.get(dsu.find(pointKey2(point)));
          if (!netNames) continue;
          for (const netName of netNames) {
            pushUniqueNetNode(netMap, netName, {
              component: ref,
              pin: pinNumber,
              x: point.x,
              y: point.y,
              source: "coordinate-fallback"
            });
          }
        }
      } catch (error) {
        if (isNetDetailTimeout(error)) throw error;
        logRecoverableError("failed to inspect schematic component pins for coordinate nets", error);
      }
    }
    return true;
  }
  async function listNetsApi(budget) {
    const schCompClass = readFirstPath([
      "SCH_PrimitiveComponent",
      "SCH_PrimitiveComponent3",
      "sch_PrimitiveComponent"
    ]);
    const schNetClass = readFirstPath(["SCH_Net", "sch_Net"]);
    if (!schCompClass) {
      throw new Error("SCH_PrimitiveComponent class not found in EasyEDA Pro API");
    }
    const comps = await awaitNetDetailStage(
      budget,
      "component_enumeration",
      () => schCompClass.getAll(void 0, true)
    );
    const netMap = /* @__PURE__ */ new Map();
    for (const c of comps || []) {
      const ref = typeof c.getState_Designator === "function" ? c.getState_Designator() : "";
      if (!ref || typeof c.getAllPins !== "function") continue;
      try {
        const pins = await awaitNetDetailStage(budget, "component_pin_read", () => c.getAllPins(), {
          component: ref
        });
        for (const p of pins || []) {
          if (typeof p.getState_PinNumber !== "function") continue;
          const pinNum = p.getState_PinNumber();
          let netName = "";
          if (typeof p.getState_OtherProperty === "function") {
            const other = p.getState_OtherProperty();
            if (other) {
              netName = String(other.net || other.Net || "");
            }
          }
          if (netName) {
            pushUniqueNetNode(netMap, netName, { component: ref, pin: pinNum });
          }
        }
      } catch (e) {
        if (isNetDetailTimeout(e)) throw e;
        logRecoverableError("failed to inspect schematic component pins", e);
      }
    }
    let physicalInventory = false;
    try {
      physicalInventory = await addCoordinateFallbackNets(netMap, comps || [], budget);
    } catch (error) {
      if (isNetDetailTimeout(error)) throw error;
      logRecoverableError("failed to infer schematic nets from wire coordinates", error);
    }
    if (!physicalInventory && schNetClass && typeof schNetClass.getAllNets === "function") {
      try {
        const allNets = await awaitNetDetailStage(
          budget,
          "net_catalog_read",
          () => schNetClass.getAllNets()
        );
        for (const n of allNets || []) {
          const netName = n.netName || n.net;
          if (netName) ensureNetEntry(netMap, String(netName));
        }
      } catch (e) {
        if (isNetDetailTimeout(e)) throw e;
        logRecoverableError("failed to inspect schematic nets", e);
      }
    }
    return Array.from(netMap, ([netName, nodes]) => ({ netName, nodes }));
  }
  function designatorOrdinal(ref, prefix) {
    if (!ref.startsWith(prefix)) return 0;
    const suffix = ref.slice(prefix.length);
    if (!/^\d+$/.test(suffix)) return 0;
    return Number.parseInt(suffix, 10);
  }
  async function assignAutoDesignator(created) {
    const pid = extractPrimitiveId(created);
    if (!pid) return void 0;
    const schCompClass = readFirstPath([
      "SCH_PrimitiveComponent",
      "SCH_PrimitiveComponent3",
      "sch_PrimitiveComponent"
    ]);
    if (!schCompClass || typeof schCompClass.get !== "function" || typeof schCompClass.modify !== "function") {
      return void 0;
    }
    let current;
    try {
      current = await schCompClass.get(pid);
    } catch (e) {
      logRecoverableError(`auto-designator: get(${pid}) failed`, e);
      return void 0;
    }
    if (!current) return void 0;
    const desig = String(safeGetState(current, "Designator") ?? "");
    const placeholder = /^([A-Za-z]+)\?+$/.exec(desig);
    if (!placeholder) return void 0;
    const prefix = placeholder[1];
    let maxN = 0;
    try {
      const comps = await schCompClass.getAll(void 0, true);
      for (const c of comps || []) {
        const ref = typeof c.getState_Designator === "function" ? String(c.getState_Designator()) : "";
        maxN = Math.max(maxN, designatorOrdinal(ref, prefix));
      }
    } catch (e) {
      logRecoverableError("auto-designator: scan failed", e);
    }
    const newDesig = `${prefix}${maxN + 1}`;
    const existingOther = safeGetState(current, "OtherProperty") || {};
    const merged = {
      x: safeGetState(current, "X"),
      y: safeGetState(current, "Y"),
      rotation: safeGetState(current, "Rotation"),
      mirror: safeGetState(current, "Mirror"),
      addIntoBom: safeGetState(current, "AddIntoBom"),
      addIntoPcb: safeGetState(current, "AddIntoPcb"),
      designator: newDesig,
      name: safeGetState(current, "Name"),
      uniqueId: safeGetState(current, "UniqueId"),
      manufacturer: safeGetState(current, "Manufacturer"),
      manufacturerId: safeGetState(current, "ManufacturerId"),
      supplier: safeGetState(current, "Supplier"),
      supplierId: safeGetState(current, "SupplierId"),
      otherProperty: existingOther
    };
    await schCompClass.modify(pid, merged);
    return newDesig;
  }
  async function applyPlacedRotation(created, rotation) {
    const rot = typeof rotation === "number" ? rotation : Number(rotation);
    if (!Number.isFinite(rot) || rot === 0) return void 0;
    const pid = extractPrimitiveId(created);
    if (!pid) return void 0;
    const schCompClass = readFirstPath([
      "SCH_PrimitiveComponent",
      "SCH_PrimitiveComponent3",
      "sch_PrimitiveComponent"
    ]);
    if (!schCompClass || typeof schCompClass.get !== "function" || typeof schCompClass.modify !== "function") {
      return void 0;
    }
    let current;
    try {
      current = await schCompClass.get(pid);
    } catch (e) {
      logRecoverableError(`apply-rotation: get(${pid}) failed`, e);
      return void 0;
    }
    if (!current) return void 0;
    const existingOther = safeGetState(current, "OtherProperty") || {};
    const merged = {
      x: safeGetState(current, "X"),
      y: safeGetState(current, "Y"),
      rotation: rot,
      mirror: safeGetState(current, "Mirror"),
      addIntoBom: safeGetState(current, "AddIntoBom"),
      addIntoPcb: safeGetState(current, "AddIntoPcb"),
      designator: safeGetState(current, "Designator"),
      name: safeGetState(current, "Name"),
      uniqueId: safeGetState(current, "UniqueId"),
      manufacturer: safeGetState(current, "Manufacturer"),
      manufacturerId: safeGetState(current, "ManufacturerId"),
      supplier: safeGetState(current, "Supplier"),
      supplierId: safeGetState(current, "SupplierId"),
      otherProperty: existingOther
    };
    await schCompClass.modify(pid, merged);
    return rot;
  }
  var DEFAULT_CONNECT_STUB_LENGTH = 10;
  function readPinPoint(pin) {
    const state = readMember(pin, "state");
    const stateRecord = isRecord2(state) ? state : void 0;
    const x = readMember(pin, "x") ?? stateRecord?.X;
    const y = readMember(pin, "y") ?? stateRecord?.Y;
    const rotation = readMember(pin, "rotation") ?? stateRecord?.Rotation;
    return {
      x: typeof x === "number" ? x : void 0,
      y: typeof y === "number" ? y : void 0,
      rotation: typeof rotation === "number" ? rotation : void 0
    };
  }
  function readPinNumber(pin) {
    const value = safeGetState(pin, "PinNumber");
    return nativeScalarString3(value);
  }
  function readPinName(pin) {
    const value = safeGetState(pin, "PinName");
    return nativeScalarString3(value);
  }
  function readPinNoConnected(pin) {
    const value = safeGetState(pin, "NoConnected");
    if (typeof value === "boolean") return value;
    if (typeof value === "string") return value.toLowerCase() === "true";
    if (typeof value === "number") return value !== 0;
    return false;
  }
  async function resolvePinNoConnectState(componentPrimitiveId, pinNumber) {
    const pins = await callFirst(
      [
        "SCH_PrimitiveComponent.getAllPinsByPrimitiveId",
        "sch_PrimitiveComponent.getAllPinsByPrimitiveId"
      ],
      componentPrimitiveId
    );
    const matches = (Array.isArray(pins) ? pins : []).filter(
      (pin2) => readPinNumber(pin2) === String(pinNumber)
    );
    if (matches.length === 0) {
      throw newBridgeError(
        "PIN_NOT_FOUND",
        `Pin "${pinNumber}" was not found on component "${componentPrimitiveId}"`,
        "Verify the component primitive ID and exact pin number with easyeda_schematic_component_pins.",
        { componentPrimitiveId, pinNumber }
      );
    }
    if (matches.length > 1) {
      throw newBridgeError(
        "PIN_AMBIGUOUS",
        `Pin number "${pinNumber}" matched ${matches.length} pins on component "${componentPrimitiveId}"`,
        "Use a component whose pin numbers are unique before applying a no-connect marker.",
        { componentPrimitiveId, pinNumber, matchCount: matches.length }
      );
    }
    const pin = matches[0];
    const pinPrimitiveId = extractPrimitiveId(pin) || nativeScalarString3(safeGetState(pin, "PrimitiveId"));
    if (!pinPrimitiveId) {
      throw newBridgeError(
        "PIN_PRIMITIVE_ID_UNAVAILABLE",
        `Pin "${pinNumber}" on component "${componentPrimitiveId}" has no addressable primitive ID`,
        "Update EasyEDA Pro or the bridge extension before retrying this write.",
        { componentPrimitiveId, pinNumber }
      );
    }
    return {
      componentPrimitiveId,
      pinPrimitiveId,
      pinNumber: readPinNumber(pin),
      pinName: readPinName(pin),
      noConnected: readPinNoConnected(pin),
      pin
    };
  }
  function publicPinNoConnectState(state) {
    return {
      componentPrimitiveId: state.componentPrimitiveId,
      pinPrimitiveId: state.pinPrimitiveId,
      pinNumber: state.pinNumber,
      pinName: state.pinName,
      noConnected: state.noConnected
    };
  }
  async function setPinNoConnectState(componentPrimitiveId, pinNumber, noConnected) {
    const before = await resolvePinNoConnectState(componentPrimitiveId, pinNumber);
    if (before.noConnected === noConnected) {
      return {
        ...publicPinNoConnectState(before),
        previousNoConnected: before.noConnected,
        changed: false,
        verified: true
      };
    }
    const pinRecord = isRecord2(before.pin) ? before.pin : void 0;
    const setter = pinRecord?.setState_NoConnected;
    const done = pinRecord?.done;
    if (typeof setter === "function" && typeof done === "function") {
      const updated = setter.call(before.pin, noConnected);
      const doneTarget = isRecord2(updated) && typeof updated.done === "function" ? updated : before.pin;
      await doneTarget.done();
    } else {
      const pinClass = readFirstPath(["SCH_PrimitivePin", "sch_PrimitivePin"]);
      if (!pinClass || typeof pinClass.modify !== "function") {
        throw newBridgeError(
          "PIN_NO_CONNECT_UNSUPPORTED",
          "The connected EasyEDA runtime does not expose a supported component-pin no-connect write path",
          "Update EasyEDA Pro or use a bridge build that supports SCH_PrimitivePin.modify.",
          { componentPrimitiveId, pinNumber }
        );
      }
      await pinClass.modify(before.pin, { noConnected });
    }
    const after = await resolvePinNoConnectState(componentPrimitiveId, pinNumber);
    if (after.noConnected !== noConnected) {
      throw newBridgeError(
        "PIN_NO_CONNECT_VERIFY_FAILED",
        `Pin "${pinNumber}" no-connect readback did not match the requested state`,
        "Do not retry blindly; inspect the pin state and EasyEDA ERC result first.",
        {
          componentPrimitiveId,
          pinNumber,
          requested: noConnected,
          observed: after.noConnected
        }
      );
    }
    return {
      ...publicPinNoConnectState(after),
      previousNoConnected: before.noConnected,
      changed: true,
      verified: true
    };
  }
  async function resolvePinEndpoint(primitiveId, pinNumber) {
    const pins = await callFirst(
      [
        "SCH_PrimitiveComponent.getAllPinsByPrimitiveId",
        "sch_PrimitiveComponent.getAllPinsByPrimitiveId"
      ],
      primitiveId
    );
    const pinList = Array.isArray(pins) ? pins : [];
    const target = pinList.find((p) => readPinNumber(p) === String(pinNumber));
    if (!target) {
      throw newBridgeError(
        "EASYEDA_API_ERROR",
        `Pin "${pinNumber}" not found on component "${primitiveId}"`,
        "Verify the primitiveId and pin number are correct (see schematic_component_pins)."
      );
    }
    const point = readPinPoint(target);
    if (point.x === void 0 || point.y === void 0) {
      throw newBridgeError(
        "EASYEDA_API_ERROR",
        `Pin "${pinNumber}" on component "${primitiveId}" did not report coordinates`,
        "The EasyEDA Pro runtime may not expose pin coordinates for this component type."
      );
    }
    const rotation = point.rotation ?? 0;
    const rad = rotation * Math.PI / 180;
    const dx = Math.round(Math.cos(rad));
    const dy = Math.round(Math.sin(rad));
    return { x: point.x, y: point.y, dx, dy };
  }
  async function connectPinToNetImpl(primitiveId, pinNumber, netName, stubLength = DEFAULT_CONNECT_STUB_LENGTH) {
    const { x, y, dx, dy } = await resolvePinEndpoint(primitiveId, pinNumber);
    const endpoint = { x: x + dx * stubLength, y: y + dy * stubLength };
    const points = [{ x, y }, endpoint];
    const collision = await findForeignNetCollision(points, netName);
    if (collision) {
      const collidedWith = collision.kind === "wire" ? "an existing wire" : "a pin or net flag/port";
      throw newBridgeError(
        "NET_COLLISION",
        `Refusing to connect pin "${pinNumber}" on "${primitiveId}" to net "${netName}": point (${collision.x}, ${collision.y}) coincides with ${collidedWith} on net "${collision.foreignNet}". EasyEDA Pro auto-merges primitives that share a coordinate, which would silently short these two nets together.`,
        `Retry with a different stubLength, or route this connection manually with schematic.addWire.`
      );
    }
    const created = await callFirst(
      ["SCH_PrimitiveWire.create", "sch_PrimitiveWire.create"],
      [x, y, endpoint.x, endpoint.y],
      netName,
      void 0,
      void 0,
      void 0
    );
    const createdId = extractPrimitiveId(created);
    return { primitiveId: createdId, endpoint };
  }
  function errorMessage2(error) {
    return error instanceof Error ? error.message : String(error);
  }
  function isConfirmedNativeNoConnect(pin) {
    return safeGetState(pin, "NoConnected") === true;
  }
  function buildConnectedNodeSet(netlistData) {
    const connectedNodes = /* @__PURE__ */ new Set();
    for (const n of netlistData) {
      for (const node of n.nodes || []) {
        connectedNodes.add(`${node.component} ${node.pin}`);
      }
    }
    return connectedNodes;
  }
  async function collectFloatingPinsForComponent(component, ref, primitiveId, connectedNodes) {
    const floating = [];
    try {
      const pins = await component.getAllPins();
      for (const p of pins || []) {
        if (typeof p.getState_PinNumber !== "function") continue;
        if (isConfirmedNativeNoConnect(p)) continue;
        const pinNum = String(p.getState_PinNumber());
        if (!connectedNodes.has(`${ref} ${pinNum}`)) {
          floating.push({ primitiveId: primitiveId || ref, designator: ref, pinNumber: pinNum });
        }
      }
    } catch {
    }
    return floating;
  }
  async function findFloatingPinsApi() {
    const netlistData = await listNetsApi();
    const connectedNodes = buildConnectedNodeSet(netlistData);
    const floatingPins = [];
    const partRefs = /* @__PURE__ */ new Set();
    const schCompClass = readFirstPath([
      "SCH_PrimitiveComponent",
      "SCH_PrimitiveComponent3",
      "sch_PrimitiveComponent"
    ]);
    if (!schCompClass || typeof schCompClass.getAll !== "function") {
      return { floatingPins, partRefs: [] };
    }
    const allComps = await schCompClass.getAll(void 0, true) || [];
    for (const c of allComps) {
      const ref = typeof c.getState_Designator === "function" ? c.getState_Designator() : "";
      if (!ref || typeof c.getAllPins !== "function") continue;
      partRefs.add(ref);
      const primitiveId = typeof c.getState_PrimitiveId === "function" ? String(c.getState_PrimitiveId()) : "";
      floatingPins.push(
        ...await collectFloatingPinsForComponent(c, ref, primitiveId, connectedNodes)
      );
    }
    return { floatingPins, partRefs: [...partRefs] };
  }
  async function getNetDetailApi(netName, operationTimeoutMs) {
    const budget = createNetDetailBudget(netName, operationTimeoutMs);
    const allNets = await listNetsApi(budget);
    const match = allNets.find((net) => net.netName === netName);
    if (!match) {
      throw newBridgeError("NET_NOT_FOUND", `Net "${netName}" not found`, "Check net name spelling.");
    }
    return match;
  }
  async function getPinNoConnectApi(componentPrimitiveId, pinNumber) {
    return publicPinNoConnectState(await resolvePinNoConnectState(componentPrimitiveId, pinNumber));
  }
  async function dispatch(method, params = {}) {
    const domainResult = await domainRouter.tryDispatch(method, params);
    if (domainResult.handled) return domainResult.value;
    switch (method) {
      case "schematic.placeComponent": {
        if (typeof params.subPartName === "string" && params.subPartName.length > 0) {
          throw newBridgeError(
            "NOT_IMPLEMENTED",
            "subPartName is not supported by this EasyEDA runtime.",
            "Omit subPartName."
          );
        }
        await needDevice(params.deviceItem);
        const createdComp = await callFirst(
          ["SCH_PrimitiveComponent.create", "sch_PrimitiveComponent.create"],
          params.deviceItem,
          params.x,
          params.y
        );
        try {
          const newDesig = await assignAutoDesignator(createdComp);
          if (newDesig && createdComp && typeof createdComp === "object") {
            createdComp.designator = newDesig;
          }
        } catch (e) {
          logRecoverableError("auto-designator failed", e);
        }
        try {
          const appliedRot = await applyPlacedRotation(createdComp, params.rotation);
          if (appliedRot !== void 0 && createdComp && typeof createdComp === "object") {
            createdComp.rotation = appliedRot;
          }
        } catch (e) {
          logRecoverableError("apply-rotation failed", e);
        }
        return createdComp;
      }
      case "schematic.addWire": {
        const rawPoints = Array.isArray(params.points) ? params.points : [];
        const netName = params.netName;
        const collision = await findForeignNetCollision(rawPoints, netName);
        if (collision) {
          const collidedWith = collision.kind === "wire" ? "an existing wire" : "a pin or net flag/port";
          throw newBridgeError(
            "NET_COLLISION",
            `Refusing to draw wire for net "${netName}": point (${collision.x}, ${collision.y}) coincides with ${collidedWith} on net "${collision.foreignNet}". EasyEDA Pro auto-merges primitives that share a coordinate (not just endpoints), which would silently short these two nets together.`,
            `Route this wire through coordinates not used by net "${collision.foreignNet}", or call schematic_nets afterward to confirm the intended topology.`
          );
        }
        const pts = rawPoints.flatMap((p) => [p.x, p.y]);
        const wireNetName = await shouldSuppressDuplicateWireNetName(rawPoints, netName) ? void 0 : netName;
        return callFirst(
          ["SCH_PrimitiveWire.create", "sch_PrimitiveWire.create"],
          pts,
          wireNetName,
          params.color,
          params.lineWidth,
          params.lineType
        );
      }
      case "schematic.addCircle":
        return callFirst(
          ["SCH_PrimitiveCircle.create", "sch_PrimitiveCircle.create"],
          params.centerX,
          params.centerY,
          params.radius,
          params.color ?? "#000000",
          params.fillColor ?? "none",
          params.lineWidth ?? 1,
          params.lineType ?? 0,
          params.fillStyle ?? "none"
        );
      case "schematic.addPolygon":
        return callFirst(
          ["SCH_PrimitivePolygon.create", "sch_PrimitivePolygon.create"],
          params.points.flatMap((p) => [p.x, p.y]),
          params.color ?? "#000000",
          params.fillColor ?? "none",
          params.lineWidth ?? 1,
          params.lineType ?? 0
        );
      case "schematic.addText": {
        const alignMode = params.alignMode === void 0 ? void 0 : requirePublicTextAlignMode(params.alignMode);
        const result = await callFirst(
          ["SCH_PrimitiveText.create", "sch_PrimitiveText.create"],
          params.x,
          params.y,
          params.content,
          params.rotation ?? 0,
          params.color ?? "#000000",
          params.fontName ?? "Arial",
          params.fontSize ?? 20,
          params.bold ?? false,
          params.italic ?? false,
          params.underline ?? false,
          alignMode
        );
        const primitiveId = extractPrimitiveId(result);
        const resultAlignMode = asPublicTextAlignMode(safeGetState(result, "AlignMode"));
        const resolvedAlignMode = resultAlignMode ?? alignMode;
        if (primitiveId && resolvedAlignMode !== void 0) {
          textAlignModeCache.set(primitiveId, resolvedAlignMode);
        }
        return result;
      }
      case "schematic.addRectangle":
        return callFirst(
          ["SCH_PrimitiveRectangle.create", "sch_PrimitiveRectangle.create"],
          params.x,
          params.y,
          params.width,
          params.height,
          params.cornerRadius ?? 0,
          params.rotation ?? 0,
          params.color ?? "#000000",
          params.fillColor ?? "none",
          params.lineWidth ?? 1,
          params.lineType ?? 0,
          params.fillStyle ?? "none"
        );
      case "schematic.setPinNoConnect":
        return setPinNoConnectState(
          params.primitiveId,
          params.pinNumber,
          params.noConnected !== false
        );
      case "schematic.createNetFlag": {
        const nfX = params.x;
        const nfY = params.y;
        const nfName = params.netName;
        const nfRotation = params.rotation ?? 0;
        const POWER_IDS = ["Power", "Ground", "AnalogGround", "ProtectGround"];
        const nfIdentification = params.identification;
        let nfResult;
        if (nfIdentification && POWER_IDS.includes(nfIdentification)) {
          nfResult = await callFirst(
            ["SCH_PrimitiveComponent.createNetFlag", "sch_PrimitiveComponent.createNetFlag"],
            nfIdentification,
            nfName,
            nfX,
            nfY,
            nfRotation
          );
        } else {
          nfResult = await callFirst(
            ["SCH_PrimitiveAttribute.createNetLabel", "sch_PrimitiveAttribute.createNetLabel"],
            nfX,
            nfY,
            nfName
          );
        }
        const nfPrimitiveId = extractPrimitiveId(nfResult);
        return {
          primitiveId: nfPrimitiveId || `netflag_${Date.now()}`,
          netName: nfName
        };
      }
      case "schematic.createNetPort": {
        const npX = params.x;
        const npY = params.y;
        const npName = params.netName;
        const npRotation = params.rotation ?? 0;
        const portTypeMap = {
          input: "IN",
          output: "OUT",
          bidirectional: "BI",
          triState: "BI",
          passive: "BI"
        };
        const npDirection = portTypeMap[params.portType ?? "passive"] ?? "BI";
        const npResult = await callFirst(
          ["SCH_PrimitiveComponent.createNetPort", "sch_PrimitiveComponent.createNetPort"],
          npDirection,
          npName,
          npX,
          npY,
          npRotation
        );
        const npPrimitiveId = extractPrimitiveId(npResult);
        return {
          primitiveId: npPrimitiveId || `netport_${Date.now()}`,
          netName: npName
        };
      }
      case "schematic.connectPinToNet": {
        const stubLength = typeof params.stubLength === "number" ? params.stubLength : void 0;
        const result = await connectPinToNetImpl(
          params.primitiveId,
          params.pinNumber,
          params.netName,
          stubLength
        );
        return {
          connected: true,
          real: true,
          primitiveId: result.primitiveId,
          endpoint: result.endpoint
        };
      }
      case "schematic.connectPinsByNet": {
        const pins = params.pins;
        const stubLength = typeof params.stubLength === "number" ? params.stubLength : void 0;
        const netName = params.netName;
        const createdPrimitiveIds = [];
        const failures = [];
        for (const pin of pins || []) {
          try {
            const result = await connectPinToNetImpl(
              pin.primitiveId,
              pin.pinNumber,
              netName,
              stubLength
            );
            createdPrimitiveIds.push(result.primitiveId);
          } catch (err) {
            logRecoverableError(
              `connectPinToNet failed for ${pin.primitiveId}/${pin.pinNumber}`,
              err
            );
            failures.push({
              primitiveId: pin.primitiveId,
              pinNumber: pin.pinNumber,
              error: err instanceof Error ? err.message : String(err)
            });
          }
        }
        return {
          count: createdPrimitiveIds.length,
          real: true,
          createdPrimitiveIds,
          failures
        };
      }
      case "schematic.setTitleBlock": {
        const SAFE_TITLE_BLOCK_FIELDS = /* @__PURE__ */ new Set([
          "Company",
          "Version",
          "Drawn",
          "Reviewed",
          "Page Size"
        ]);
        const fields = params.fields ?? {};
        const unsafeKeys = Object.keys(fields).filter((key) => !SAFE_TITLE_BLOCK_FIELDS.has(key));
        if (unsafeKeys.length > 0) {
          throw newBridgeError(
            "INVALID_PARAMS",
            `schematic.setTitleBlock refuses to write field(s): ${unsafeKeys.join(", ")}. These are read-only through this API (writes either no-op or throw natively) and a past attempt to round-trip them corrupted a real project's title block.`,
            `Only these fields are writable: ${[...SAFE_TITLE_BLOCK_FIELDS].join(", ")}.`
          );
        }
        const pageInfo = await callFirst([
          "DMT_Schematic.getCurrentSchematicPageInfo",
          "dmt_Schematic.getCurrentSchematicPageInfo"
        ]).catch(() => void 0);
        if (!pageInfo) {
          throw newBridgeError(
            "SCHEMATIC_NOT_FOCUSED",
            "schematic.setTitleBlock requires the schematic tab to be the focused/active document.",
            "Click into the schematic document in EasyEDA Pro, then retry."
          );
        }
        const showTitleBlock = typeof params.showTitleBlock === "boolean" ? params.showTitleBlock : true;
        const result = await callFirst(
          [
            "DMT_Schematic.modifySchematicPageTitleBlock",
            "dmt_Schematic.modifySchematicPageTitleBlock"
          ],
          showTitleBlock,
          fields
        );
        return { success: result === true };
      }
      case "schematic.syncToPcb": {
        const schInfo = await callFirst([
          "DMT_Schematic.getCurrentSchematicInfo",
          "dmt_Schematic.getCurrentSchematicInfo"
        ]).catch(() => void 0);
        if (!schInfo) {
          throw newBridgeError(
            "SCHEMATIC_NOT_FOCUSED",
            "schematic.syncToPcb requires the schematic tab to be the focused/active document in EasyEDA Pro.",
            "Click into the schematic document in EasyEDA Pro, then retry."
          );
        }
        const result = await callFirst(["SCH_Document.importChanges", "sch_Document.importChanges"]);
        return { synced: result !== false };
      }
      default:
        throw newBridgeError(
          "METHOD_NOT_ALLOWED",
          `Unsupported bridge method: ${method}`,
          "Update the extension dispatcher or call a supported method."
        );
    }
  }
  function createDispatcher(toolkit) {
    ({ callFirst, readFirstPath, inspectApiInventory, callAllowedApi } = createApiRuntime(
      toolkit,
      newBridgeError
    ));
    boardInspection = createBoardInspectionOperations({
      readFirstPath,
      getGlobal: () => toolkit.getGlobal(),
      createBridgeError: newBridgeError
    });
    const normalizeBinaryResult2 = createBinaryResultNormalizer({
      getBridgeMaxPayloadSize: () => toolkit.getBridgeMaxPayloadSize(),
      createBridgeError: newBridgeError
    });
    canvasOperations = createCanvasOperations({
      callFirst,
      normalizeBinaryResult: toolkit.normalizeCanvasBinaryResult ?? normalizeBinaryResult2,
      createBridgeError: newBridgeError
    });
    designRuleCheckOperations = createDesignRuleCheckOperations({
      callFirst,
      createBridgeError: newBridgeError,
      logRecoverableError,
      errorMessage: errorMessage2,
      findFloatingPins: findFloatingPinsApi
    });
    exportOperations = createExportOperations({
      callFirst,
      normalizeBinaryResult: normalizeBinaryResult2,
      createBridgeError: newBridgeError
    });
    pcbReadOperations = createPcbReadOperations({
      requireActivePcbContext: () => boardInspection.requireActivePcbContext(),
      readFirstPath,
      readState: safeGetState
    });
    pcbMutationOperations = createPcbMutationOperations({
      callFirst,
      readFirstPath,
      requireActivePcbContext: () => boardInspection.requireActivePcbContext(),
      deletePrimitives: (ids) => pcbReadOperations.deletePrimitives(ids)
    });
    pcbWriteOperations = createPcbWriteOperations({
      callFirst,
      extractPrimitiveId,
      createBridgeError: newBridgeError
    });
    projectOperations = createProjectOperations({ callFirst });
    schematicComponentInspection = createSchematicComponentInspectionOperations({
      readFirstPath,
      readState: safeGetState
    });
    schematicInspection = createSchematicInspectionOperations({
      callFirst,
      readFirstPath,
      readState: safeGetState,
      extractPrimitiveId,
      createBridgeError: newBridgeError
    });
    schematicTransactionOperations = createSchematicTransactionOperations({
      callFirst,
      readFirstPath,
      readState: safeGetState,
      extractPrimitiveId,
      readComponentType,
      readPinPoint,
      createBridgeError: newBridgeError,
      logRecoverableError,
      asPublicTextAlignMode,
      requirePublicTextAlignMode,
      getCachedTextAlignMode: (primitiveId) => textAlignModeCache.get(primitiveId),
      setCachedTextAlignMode: (primitiveId, alignMode) => textAlignModeCache.set(primitiveId, alignMode),
      deleteCachedTextAlignMode: (primitiveId) => textAlignModeCache.delete(primitiveId)
    });
    readOnlyOperations = createReadOnlyOperations({
      callFirst,
      schematicTransactionOperations,
      schematicComponentInspection,
      schematicInspection,
      listNets: async () => await listNetsApi(),
      getNetDetail: getNetDetailApi,
      getPinNoConnect: getPinNoConnectApi,
      findFloatingPins: findFloatingPinsApi,
      runSchematicCheck: () => designRuleCheckOperations.runSchematicCheck(),
      logRecoverableError
    });
    systemApiOperations = createSystemApiOperations({
      toolkit,
      methodList: METHOD_LIST,
      buildId: BUILD_ID,
      inspectApiInventory,
      callAllowedApi,
      readFirstPath,
      summarizeWirePrimitive,
      createBridgeError: newBridgeError,
      logRecoverableError
    });
    domainRouter = createDispatcherDomainRouter({
      projectOperations,
      readOnlyOperations,
      schematicTransactionOperations,
      boardInspection,
      exportOperations,
      designRuleCheckOperations,
      canvasOperations,
      pcbWriteOperations,
      pcbMutationOperations,
      pcbReadOperations,
      systemApiOperations
    });
    textAlignModeCache.clear();
    log(`dispatcher initialized (build ${BUILD_ID}, ${METHOD_LIST.length} methods)`);
    return {
      dispatch,
      methodList: [...METHOD_LIST],
      buildId: BUILD_ID
    };
  }

  // src/capture-binary-result.ts
  var PAYLOAD_SAFETY_MARGIN = 0.6;
  var MAX_MCP_IMAGE_RESULT_BYTES = 1048576;
  var MAX_DOWNSAMPLE_ATTEMPTS = 8;
  function payloadTooLargeError(byteLength, budget) {
    return Object.assign(
      new Error(
        `Canvas capture is ${byteLength} bytes and exceeds the safe ${budget}-byte image budget, but this EasyEDA runtime cannot safely downsample it. Use a smaller capture region or lower the rendered viewport scale, then retry.`
      ),
      {
        code: "PAYLOAD_TOO_LARGE",
        suggestion: "Use a smaller capture region or lower the rendered viewport scale, then retry."
      }
    );
  }
  async function downsampleBlob(blob, budget) {
    const createBitmap = globalThis.createImageBitmap;
    const Canvas = globalThis.OffscreenCanvas;
    if (typeof createBitmap !== "function" || typeof Canvas !== "function") {
      throw payloadTooLargeError(blob.size, budget);
    }
    let bitmap;
    try {
      bitmap = await createBitmap(blob);
    } catch {
      throw payloadTooLargeError(blob.size, budget);
    }
    const originalDimensions = { width: bitmap.width, height: bitmap.height };
    try {
      if (bitmap.width <= 0 || bitmap.height <= 0) throw payloadTooLargeError(blob.size, budget);
      let width = bitmap.width;
      let height = bitmap.height;
      let currentBytes = blob.size;
      for (let attempt = 0; attempt < MAX_DOWNSAMPLE_ATTEMPTS; attempt += 1) {
        const scale = Math.min(0.95, Math.sqrt(budget / currentBytes));
        width = Math.max(1, Math.floor(width * scale));
        height = Math.max(1, Math.floor(height * scale));
        const canvas = new Canvas(width, height);
        const context = canvas.getContext("2d");
        if (!context) throw payloadTooLargeError(blob.size, budget);
        context.drawImage(bitmap, 0, 0, width, height);
        let resized;
        try {
          resized = await canvas.convertToBlob({ type: "image/png" });
        } catch {
          throw payloadTooLargeError(blob.size, budget);
        }
        if (resized.size <= budget) {
          return { blob: resized, originalDimensions, imageDimensions: { width, height } };
        }
        if (width === 1 && height === 1) break;
        currentBytes = resized.size;
      }
      throw payloadTooLargeError(blob.size, budget);
    } finally {
      bitmap.close();
    }
  }
  async function normalizeCanvasBinaryResult(value, fallbackFileName, maxPayloadSize) {
    if (!isBlobLike(value)) return normalizeBinaryResult(value, fallbackFileName);
    const budget = Math.max(
      1,
      Math.floor(Math.min(maxPayloadSize, MAX_MCP_IMAGE_RESULT_BYTES) * PAYLOAD_SAFETY_MARGIN)
    );
    if (value.size <= budget) {
      const normalized2 = await normalizeBinaryResult(value, fallbackFileName);
      return normalized2 && typeof normalized2 === "object" ? { ...normalized2, downsampled: false, payloadBudgetBytes: budget } : normalized2;
    }
    const resized = await downsampleBlob(value, budget);
    const normalized = await normalizeBinaryResult(resized.blob, fallbackFileName);
    return normalized && typeof normalized === "object" ? {
      ...normalized,
      downsampled: true,
      originalDimensions: resized.originalDimensions,
      imageDimensions: resized.imageDimensions,
      payloadBudgetBytes: budget
    } : normalized;
  }

  // src/runtime-timers.ts
  function createRuntimeTimers(getEasyedaTimerApi, nativeGlobal = globalThis, idPrefix = "easyeda-mcp-pro") {
    let sequence = 0;
    const nextId = (kind) => `${idPrefix}:${kind}:${++sequence}`;
    return {
      setTimeout(callback, delayMs) {
        const api2 = getEasyedaTimerApi();
        if (api2?.setTimeoutTimer) {
          const id = nextId("timeout");
          if (api2.setTimeoutTimer(id, delayMs, callback) !== false) {
            return { source: "easyeda", kind: "timeout", id };
          }
        }
        if (typeof nativeGlobal.setTimeout === "function") {
          return {
            source: "native",
            kind: "timeout",
            handle: nativeGlobal.setTimeout.call(nativeGlobal, callback, delayMs)
          };
        }
        throw new Error("No timeout scheduler is available in the EasyEDA extension runtime.");
      },
      clearTimeout(handle) {
        if (!handle) return;
        if (handle.source === "easyeda") {
          getEasyedaTimerApi()?.clearTimeoutTimer?.(handle.id);
          return;
        }
        nativeGlobal.clearTimeout?.call(nativeGlobal, handle.handle);
      },
      setInterval(callback, delayMs) {
        const api2 = getEasyedaTimerApi();
        if (api2?.setIntervalTimer) {
          const id = nextId("interval");
          if (api2.setIntervalTimer(id, delayMs, callback) !== false) {
            return { source: "easyeda", kind: "interval", id };
          }
        }
        if (typeof nativeGlobal.setInterval === "function") {
          return {
            source: "native",
            kind: "interval",
            handle: nativeGlobal.setInterval.call(nativeGlobal, callback, delayMs)
          };
        }
        throw new Error("No interval scheduler is available in the EasyEDA extension runtime.");
      },
      clearInterval(handle) {
        if (!handle) return;
        if (handle.source === "easyeda") {
          getEasyedaTimerApi()?.clearIntervalTimer?.(handle.id);
          return;
        }
        nativeGlobal.clearInterval?.call(nativeGlobal, handle.handle);
      }
    };
  }

  // src/index.ts
  var EXTENSION_INFO = {
    extensionVersion: "1.2.0"
    // x-release-please-version
  };
  function getWsApi() {
    return typeof SYS_WebSocket !== "undefined" ? SYS_WebSocket : readPath(getGlobal(), "sys_WebSocket");
  }
  function getSysMessage() {
    return typeof SYS_Message !== "undefined" ? SYS_Message : readPath(getGlobal(), "sys_Message");
  }
  function getInfoToastType() {
    const info = typeof ESYS_ToastMessageType !== "undefined" ? ESYS_ToastMessageType.INFO : void 0;
    return typeof info === "string" ? info : "info";
  }
  var BRIDGE_PROTOCOL = "easyeda-mcp-pro.bridge";
  var BRIDGE_VERSION = "1.0.0";
  var BRIDGE_CONTRACT_VERSION = 1;
  var SOCKET_ID = "easyeda-mcp-pro-bridge";
  var socketHandle = null;
  var connectedPort = null;
  var preferredPort = BRIDGE_PORT;
  var connectionState = "disconnected";
  var activeConnectPromise = null;
  var reconnectAttempts = 0;
  var connectRunId = 0;
  var manualDisconnectRequested = false;
  var reconnectTimer = null;
  var heartbeatTimer = null;
  var lastServerActivityMs = 0;
  var lastLocalConnectionDiagnostic = null;
  var externalInteractionWarningShown = false;
  var bridgeMaxPayloadSize = 1048576;
  var serverSupportsChunking = false;
  var maxAggregatePayloadSize = 1048576;
  var serverHotSwapEnabled = false;
  function getGlobal() {
    if (typeof eda !== "undefined" && eda) return eda;
    return globalThis;
  }
  var runtimeTimers = createRuntimeTimers(
    () => readPath(getGlobal(), "sys_Timer"),
    globalThis,
    SOCKET_ID
  );
  function recordLocalConnectionDiagnostic(diagnostic) {
    log(`Local bridge connection phase ${diagnostic.phase}`, {
      port: diagnostic.port,
      transport: diagnostic.transport,
      message: diagnostic.message
    });
    const effectivePriority = diagnostic.priority + (diagnostic.port === preferredPort ? 1e3 : 0);
    if (!lastLocalConnectionDiagnostic || effectivePriority >= lastLocalConnectionDiagnostic.priority) {
      lastLocalConnectionDiagnostic = { ...diagnostic, priority: effectivePriority };
    }
  }
  function localConnectionDiagnosticSuffix() {
    if (!lastLocalConnectionDiagnostic) return "";
    return ` \u2014 ${lastLocalConnectionDiagnostic.message}`;
  }
  function showToast(message) {
    const safeMessage = String(message);
    const messageType = getInfoToastType();
    const sysMessage = getSysMessage();
    if (sysMessage?.showToastMessage) {
      try {
        sysMessage.showToastMessage(safeMessage, messageType);
        return;
      } catch (error) {
        log("sysMessage.showToastMessage failed", { message: safeMessage, error: String(error) });
      }
    }
    const toastMessage = readPath(getGlobal(), "sys_ToastMessage");
    if (toastMessage?.showMessage) {
      try {
        toastMessage.showMessage(safeMessage, messageType);
        return;
      } catch (error) {
        log("toastMessage.showMessage failed", { message: safeMessage, error: String(error) });
      }
    }
    log(safeMessage);
  }
  function showExternalInteractionHintOnce(error) {
    const message = "MCP Bridge needs EasyEDA External Interactions permission. Enable it in Extension Manager for MCP Pro Bridge.";
    log(message, error);
    if (externalInteractionWarningShown) return;
    externalInteractionWarningShown = true;
    showToast(message);
  }
  var dispatcherToolkit = {
    getEda: () => {
      if (typeof eda !== "undefined" && eda) return eda;
      return globalThis.eda;
    },
    getEDA: () => {
      if (typeof EDA !== "undefined" && EDA) return EDA;
      return globalThis.EDA;
    },
    getApi: () => {
      if (typeof api !== "undefined" && api) return api;
      return globalThis.api;
    },
    getGlobal: () => getGlobal(),
    log,
    showToast,
    // With chunked sends (A5) a single logical payload may span many frames, so
    // the dispatcher's binary self-limit is the aggregate cap, not the frame cap.
    getBridgeMaxPayloadSize: () => serverSupportsChunking ? maxAggregatePayloadSize : bridgeMaxPayloadSize,
    normalizeCanvasBinaryResult: (value, fallbackFileName) => normalizeCanvasBinaryResult(value, fallbackFileName, bridgeMaxPayloadSize),
    getBridgeVersion: () => BRIDGE_VERSION
  };
  var bakedDispatcher = createDispatcher(dispatcherToolkit);
  var activeDispatcher = bakedDispatcher;
  function dispatchViaActive(method, params = {}) {
    return activeDispatcher.dispatch(method, params);
  }
  var HOTSWAP_COMPILED = false;
  var hotSwapBuffer = null;
  var activeMethodListHash = "";
  async function sha256Hex(text) {
    const subtle = typeof crypto !== "undefined" ? crypto.subtle : void 0;
    if (!subtle) {
      throw newLoaderError(
        "EASYEDA_API_ERROR",
        "crypto.subtle is not available in this runtime",
        "Hot swap and method-list hashing require a secure context."
      );
    }
    const digest = await subtle.digest("SHA-256", new TextEncoder().encode(text));
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }
  function newLoaderError(code, message, suggestion) {
    const error = new Error(message);
    Object.assign(error, { code, suggestion });
    return error;
  }
  function compareCodeUnits(a, b) {
    if (a === b) return 0;
    return a < b ? -1 : 1;
  }
  async function refreshMethodListHash() {
    try {
      const sorted = [...activeDispatcher.methodList].sort(compareCodeUnits);
      activeMethodListHash = (await sha256Hex(sorted.join(","))).slice(0, 16);
    } catch (error) {
      log("failed to compute method list hash", String(error));
      activeMethodListHash = "";
    }
  }
  function loaderStatus() {
    return {
      loaderVersion: EXTENSION_INFO.extensionVersion,
      bridgeVersion: BRIDGE_VERSION,
      activeDispatcher: activeDispatcher === bakedDispatcher ? "baked" : "pushed",
      buildId: activeDispatcher.buildId,
      bakedBuildId: bakedDispatcher.buildId,
      methodCount: activeDispatcher.methodList.length,
      methodListHash: activeMethodListHash,
      hotSwapCompiled: HOTSWAP_COMPILED,
      hotSwapEnabled: HOTSWAP_COMPILED && serverHotSwapEnabled
    };
  }
  function assertHotSwapAllowed() {
    if (!HOTSWAP_COMPILED) {
      throw newLoaderError(
        "DEV_MODE_REQUIRED",
        "This extension build does not include hot-swap support.",
        "Import a dev build of the extension (scripts/build.mjs with MCP_DEV_HOTSWAP=true)."
      );
    }
    if (!serverHotSwapEnabled) {
      throw newLoaderError(
        "DEV_MODE_REQUIRED",
        "The connected MCP server has not enabled hot swap.",
        "Start the server with BRIDGE_HOT_SWAP_ENABLED=true (non-production only)."
      );
    }
  }
  async function commitHotSwap() {
    const buffer = hotSwapBuffer;
    hotSwapBuffer = null;
    if (!buffer) {
      throw newLoaderError(
        "INVALID_PARAMS",
        "No hot-swap transfer in progress",
        "Send system.hotSwap.begin and all chunks before commit."
      );
    }
    if (buffer.received !== buffer.totalChunks) {
      throw newLoaderError(
        "INVALID_PARAMS",
        `Hot-swap transfer incomplete: ${buffer.received}/${buffer.totalChunks} chunks received`,
        "Resend the bundle from system.hotSwap.begin."
      );
    }
    const source = buffer.chunks.join("");
    const actualByteLength = new TextEncoder().encode(source).byteLength;
    if (actualByteLength !== buffer.byteLength) {
      throw newLoaderError(
        "INVALID_PARAMS",
        `Hot-swap bundle size mismatch: expected ${buffer.byteLength} bytes, got ${actualByteLength}`,
        "Resend the bundle from system.hotSwap.begin."
      );
    }
    const actualSha = await sha256Hex(source);
    if (actualSha !== buffer.sha256) {
      throw newLoaderError(
        "UNAUTHORIZED",
        "Hot-swap bundle sha256 verification failed",
        "Resend the bundle from system.hotSwap.begin."
      );
    }
    const globalScope = globalThis;
    delete globalScope.__mcpDispatcherFactory;
    const AsyncFunction = Object.getPrototypeOf(async function() {
    }).constructor;
    try {
      const run = new AsyncFunction(source);
      await run();
    } catch (error) {
      delete globalScope.__mcpDispatcherFactory;
      throw newLoaderError(
        "EASYEDA_API_ERROR",
        `Hot-swap bundle failed to evaluate: ${String(error)}`,
        "The previous dispatcher remains active. Fix the bundle and push again."
      );
    }
    const factory = globalScope.__mcpDispatcherFactory;
    delete globalScope.__mcpDispatcherFactory;
    if (typeof factory !== "function") {
      throw newLoaderError(
        "EASYEDA_API_ERROR",
        "Hot-swap bundle did not register __mcpDispatcherFactory",
        "Build the bundle from dispatcher-entry.ts (pnpm build in the extension package)."
      );
    }
    const candidate = factory(dispatcherToolkit);
    if (!candidate || typeof candidate.dispatch !== "function" || !Array.isArray(candidate.methodList) || typeof candidate.buildId !== "string") {
      throw newLoaderError(
        "EASYEDA_API_ERROR",
        "Hot-swap factory returned an invalid dispatcher",
        "The previous dispatcher remains active. Fix the bundle and push again."
      );
    }
    activeDispatcher = candidate;
    await refreshMethodListHash();
    log(`hot-swapped dispatcher to build ${candidate.buildId}`);
    showToast(`MCP Bridge: dispatcher hot-swapped (${candidate.buildId})`);
    return {
      swapped: true,
      buildId: candidate.buildId,
      methodCount: candidate.methodList.length,
      methodListHash: activeMethodListHash
    };
  }
  async function handleLoaderMethod(method, params) {
    switch (method) {
      case "system.loaderStatus":
        return { handled: true, result: loaderStatus() };
      case "system.hotSwap.begin": {
        assertHotSwapAllowed();
        const totalChunks = Number(params.totalChunks);
        const byteLength = Number(params.byteLength);
        const sha256 = String(params.sha256 ?? "");
        const buildId = String(params.buildId ?? "");
        if (!Number.isInteger(totalChunks) || totalChunks < 1 || totalChunks > 4096 || !Number.isInteger(byteLength) || byteLength < 1 || !/^[0-9a-f]{64}$/.test(sha256) || !buildId) {
          throw newLoaderError(
            "INVALID_PARAMS",
            "system.hotSwap.begin requires totalChunks, byteLength, sha256 and buildId",
            "Use the server-side pushDispatcher helper."
          );
        }
        hotSwapBuffer = {
          chunks: new Array(totalChunks),
          totalChunks,
          byteLength,
          sha256,
          buildId,
          received: 0,
          bytes: 0
        };
        return { handled: true, result: { ready: true, buildId } };
      }
      case "system.hotSwap.chunk": {
        assertHotSwapAllowed();
        const buffer = hotSwapBuffer;
        const seq = Number(params.seq);
        const data = typeof params.data === "string" ? params.data : void 0;
        if (!buffer) {
          throw newLoaderError(
            "INVALID_PARAMS",
            "No hot-swap transfer in progress",
            "Send system.hotSwap.begin first."
          );
        }
        if (!Number.isInteger(seq) || seq < 0 || seq >= buffer.totalChunks || data === void 0) {
          throw newLoaderError(
            "INVALID_PARAMS",
            "system.hotSwap.chunk requires a valid seq and data",
            "Use the server-side pushDispatcher helper."
          );
        }
        if (buffer.chunks[seq] === void 0) {
          buffer.received += 1;
          buffer.bytes += data.length;
        } else {
          buffer.bytes += data.length - (buffer.chunks[seq]?.length ?? 0);
        }
        if (buffer.bytes > buffer.byteLength * 4) {
          hotSwapBuffer = null;
          throw newLoaderError(
            "INVALID_PARAMS",
            "Hot-swap transfer exceeded the announced byteLength budget",
            "Resend the bundle from system.hotSwap.begin."
          );
        }
        buffer.chunks[seq] = data;
        return {
          handled: true,
          result: { received: buffer.received, totalChunks: buffer.totalChunks }
        };
      }
      case "system.hotSwap.commit": {
        assertHotSwapAllowed();
        return { handled: true, result: await commitHotSwap() };
      }
      case "system.hotSwap.revert": {
        assertHotSwapAllowed();
        hotSwapBuffer = null;
        const wasPushed = activeDispatcher !== bakedDispatcher;
        activeDispatcher = bakedDispatcher;
        await refreshMethodListHash();
        if (wasPushed) {
          log("reverted to baked dispatcher");
          showToast("MCP Bridge: reverted to baked dispatcher");
        }
        return {
          handled: true,
          result: { reverted: wasPushed, buildId: activeDispatcher.buildId }
        };
      }
      default:
        return { handled: false };
    }
  }
  var remoteRelayClient = null;
  function requestRemoteApproval(prompt) {
    const dialog = readPath(getGlobal(), "sys_Dialog");
    const expiresAtMs = Date.parse(prompt.expiresAt);
    if (!Number.isFinite(expiresAtMs) || expiresAtMs <= Date.now()) {
      return Promise.resolve("timeout");
    }
    const showConfirmationMessage = dialog?.showConfirmationMessage?.bind(dialog);
    if (!showConfirmationMessage) {
      log("Remote approval dialog unavailable", { toolName: prompt.toolName });
      showToast("Remote approval dialog is unavailable; request rejected.");
      return Promise.resolve("rejected");
    }
    return new Promise((resolve) => {
      let settled = false;
      const timer = setTimeout(() => finish("timeout"), Math.max(0, expiresAtMs - Date.now()));
      function finish(decision) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(decision);
      }
      const project = prompt.activeProject?.projectName ?? "current EasyEDA project";
      const summary = [
        prompt.actionSummary,
        `Method: ${prompt.toolName}`,
        `Risk: ${prompt.riskLevel}`,
        `Project: ${project}`,
        `Input hash: ${prompt.inputHash.slice(0, 12)}`
      ].join("\n");
      try {
        showConfirmationMessage(
          summary,
          "Remote MCP Approval",
          "Approve",
          "Reject",
          (mainButtonClicked) => finish(mainButtonClicked ? "approved" : "rejected")
        );
      } catch (error) {
        log("Remote approval dialog failed", error);
        finish("rejected");
      }
    });
  }
  function getRemoteRelayClient() {
    remoteRelayClient ?? (remoteRelayClient = new RemoteRelayClient({
      extensionVersion: EXTENSION_INFO.extensionVersion,
      log,
      showToast,
      readActiveProject: readRemoteActiveProject,
      executeToolRequest: (toolName, input) => dispatchViaActive(toolName, isRecord2(input) ? input : {}),
      requestApproval: requestRemoteApproval,
      timers: runtimeTimers,
      createWebSocket: (url) => {
        const WebSocketCtor = globalThis.WebSocket;
        if (typeof WebSocketCtor !== "function") {
          throw new Error("WebSocket is unavailable in the EasyEDA extension runtime.");
        }
        return new WebSocketCtor(url);
      }
    }));
    return remoteRelayClient;
  }
  function readRemoteActiveProject() {
    const href = typeof location !== "undefined" ? location.href : void 0;
    const title = typeof document !== "undefined" ? document.title : void 0;
    const projectName = title && title.trim() ? title.trim() : void 0;
    if (!href && !projectName) return void 0;
    const lower = `${href ?? ""} ${projectName ?? ""}`.toLowerCase();
    const documentType = lower.includes("pcb") ? "pcb" : lower.includes("sch") ? "schematic" : "unknown";
    return { projectName, documentType, url: href };
  }
  function connectRemoteRelayInternal(mode = "hosted", relayUrl, pairingCode) {
    getRemoteRelayClient().connect({ mode, relayUrl, pairingCode });
  }
  function disconnectRemoteRelayInternal() {
    getRemoteRelayClient().disconnect("user_disabled");
    showToast("Remote Relay disabled");
  }
  function showRemoteRelayStatusInternal() {
    const status = getRemoteRelayClient().getStatus();
    const project = status.activeProject?.projectName ?? "no active project detected";
    const retry = status.nextReconnectDelayMs !== void 0 ? ` | retry: ${Math.ceil(status.nextReconnectDelayMs / 1e3)}s` : "";
    const attempts = status.reconnectAttempts && status.reconnectAttempts > 0 ? ` | attempts: ${status.reconnectAttempts}` : "";
    const error = status.lastError ? ` | last error: ${status.lastError}` : "";
    showToast(
      `Remote Relay: ${status.mode}/${status.state} | project: ${project}${attempts}${retry}${error}`
    );
  }
  function createSocket(id, url, onOpen, onMessage, onClose, onError, options = {}) {
    const sysWs = getWsApi();
    if (!options.skipRegister && sysWs?.register && sysWs.send) {
      let openFired = false;
      const fireOpen = () => {
        if (openFired) return;
        openFired = true;
        onOpen();
      };
      try {
        sysWs.register(
          id,
          url,
          (event) => onMessage(String(isRecord2(event) && "data" in event ? event.data : event)),
          fireOpen
        );
        return { type: "easyeda-register", id };
      } catch (err) {
        showExternalInteractionHintOnce(err);
        log("register() threw, falling through", err);
      }
    }
    if (sysWs?.create) {
      try {
        const socket = sysWs.create(url);
        socket.onopen = onOpen;
        socket.onmessage = (event) => onMessage(String(isRecord2(event) ? event.data : event));
        socket.onclose = onClose;
        socket.onerror = onError;
        return { type: "easyeda-create", raw: socket };
      } catch (err) {
        log("create() threw, falling through", err);
      }
    }
    const BrowserWebSocketCtor = globalThis.WebSocket;
    if (typeof BrowserWebSocketCtor === "function") {
      try {
        const socket = new BrowserWebSocketCtor(url);
        socket.onopen = onOpen;
        socket.onmessage = (event) => onMessage(String(event.data));
        socket.onclose = onClose;
        socket.onerror = onError;
        return { type: "browser", raw: socket };
      } catch (err) {
        log("WebSocket() threw", err);
      }
    }
    return null;
  }
  var chunkIdCounter = 0;
  function send(data) {
    const payload = JSON.stringify(data);
    if (serverSupportsChunking && payload.length > Math.floor(bridgeMaxPayloadSize / 2)) {
      const chunkSize = Math.max(16384, Math.floor(bridgeMaxPayloadSize / 4));
      const total = Math.ceil(payload.length / chunkSize);
      const id = `chk_${Date.now()}_${++chunkIdCounter}`;
      for (let seq = 0; seq < total; seq += 1) {
        sendRaw(
          JSON.stringify({
            type: "chunk",
            id,
            seq,
            total,
            data: payload.slice(seq * chunkSize, (seq + 1) * chunkSize)
          })
        );
      }
      return;
    }
    sendRaw(payload);
  }
  function sendRaw(payload) {
    const sysWs = getWsApi();
    if (socketHandle?.type === "easyeda-register" && sysWs?.send) {
      try {
        sysWs.send(socketHandle.id ?? SOCKET_ID, payload);
        return;
      } catch (err) {
        log("sysWs.send threw exception", err);
        recoverConnection("Bridge send failed; reconnecting");
      }
      return;
    }
    try {
      socketHandle?.raw?.send?.(payload);
    } catch (err) {
      log("socket raw send threw exception", err);
      recoverConnection("Bridge socket send failed; reconnecting");
    }
  }
  function closeHandle(handle) {
    if (!handle) return;
    const sysWs = getWsApi();
    if (handle.type === "easyeda-register" && sysWs?.close) {
      try {
        sysWs.close(handle.id ?? SOCKET_ID);
        return;
      } catch (err) {
        log("sysWs.close threw exception", err);
      }
      return;
    }
    try {
      handle.raw?.close?.();
    } catch (err) {
      log("handle raw close threw exception", err);
    }
  }
  function closeSocket() {
    closeHandle(socketHandle);
    socketHandle = null;
    connectedPort = null;
    connectionState = "disconnected";
    lastServerActivityMs = 0;
  }
  function recoverConnection(reason) {
    const wasConnected = connectionState === "connected" && connectedPort !== null;
    const wasConnecting = connectionState === "connecting";
    if (!wasConnected && !wasConnecting && !socketHandle) return;
    log(reason);
    stopHeartbeat();
    closeHandle(socketHandle);
    socketHandle = null;
    connectedPort = null;
    lastServerActivityMs = 0;
    if (wasConnecting) {
      connectionState = "connecting";
      return;
    }
    connectionState = "disconnected";
    if (shouldReconnectAfterSocketFailure({
      wasConnected,
      manualDisconnectRequested,
      autoConnectEnabled
    })) {
      scheduleReconnect();
    }
  }
  function sendHandshake() {
    const sessionToken = typeof BRIDGE_SESSION_TOKEN !== "undefined" ? BRIDGE_SESSION_TOKEN : void 0;
    const handshake = {
      type: "handshake",
      protocol: BRIDGE_PROTOCOL,
      protocolVersion: BRIDGE_VERSION,
      contractVersion: BRIDGE_CONTRACT_VERSION,
      clientName: "easyeda-mcp-pro",
      extensionVersion: EXTENSION_INFO.extensionVersion,
      easyedaVersion: getEasyedaVersion(),
      devMode: false,
      loaderVersion: EXTENSION_INFO.extensionVersion
    };
    if (activeMethodListHash) {
      handshake.methodListHash = activeMethodListHash;
    }
    if (sessionToken) {
      handshake.sessionToken = sessionToken;
    }
    send(handshake);
  }
  function getEasyedaVersion() {
    const maybeVersion = readPath(getGlobal(), "sys_Environment.getVersion");
    if (typeof maybeVersion === "function") {
      try {
        return String(maybeVersion());
      } catch (error) {
        log("failed to read EasyEDA version", String(error));
        return void 0;
      }
    }
    return void 0;
  }
  function startHeartbeat() {
    stopHeartbeat();
    lastServerActivityMs = Date.now();
    heartbeatTimer = runtimeTimers.setInterval(() => {
      if (connectedPort === null) return;
      const nowMs = Date.now();
      if (hasHeartbeatTimedOut(lastServerActivityMs, nowMs)) {
        recoverConnection(`Bridge heartbeat timeout; silent for ${nowMs - lastServerActivityMs}ms`);
        return;
      }
      send({ type: "heartbeat", timestamp: nowMs, source: "extension" });
    }, HEARTBEAT_INTERVAL_MS);
  }
  function stopHeartbeat() {
    if (heartbeatTimer) {
      runtimeTimers.clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
    lastServerActivityMs = 0;
  }
  function bridgeErrorMessage(error) {
    if (error instanceof Error) return error.message;
    if (isRecord2(error) && typeof error.message === "string") return error.message;
    return String(error);
  }
  async function handleRequest(message) {
    const startedAt = Date.now();
    try {
      const loaderResult = await handleLoaderMethod(message.method, message.params ?? {});
      const result = loaderResult.handled ? loaderResult.result : await activeDispatcher.dispatch(message.method, message.params);
      send({
        id: message.id,
        type: "response",
        ok: true,
        result,
        durationMs: Date.now() - startedAt
      });
    } catch (error) {
      const record = isRecord2(error) ? error : {};
      const response = {
        id: message.id,
        type: "response",
        ok: false,
        error: {
          code: String(record.code ?? "EASYEDA_API_ERROR"),
          message: bridgeErrorMessage(error),
          suggestion: String(record.suggestion ?? "Check EasyEDA Pro and extension logs."),
          data: record.data
        },
        durationMs: Date.now() - startedAt
      };
      send(response);
    }
  }
  function applyHelloPayload(record) {
    if (record.contractVersion !== BRIDGE_CONTRACT_VERSION) {
      log("Bridge hello contract version mismatch", {
        expected: BRIDGE_CONTRACT_VERSION,
        actual: record.contractVersion
      });
    }
    const supportedVersions = Array.isArray(record.supportedProtocolVersions) ? record.supportedProtocolVersions : [];
    if (!supportedVersions.includes(BRIDGE_VERSION)) {
      log("Bridge hello does not include this extension protocol version", {
        protocolVersion: BRIDGE_VERSION,
        supportedProtocolVersions: supportedVersions
      });
    }
    if (typeof record.maxPayloadSize === "number" && record.maxPayloadSize > 0) {
      bridgeMaxPayloadSize = record.maxPayloadSize;
    }
    serverSupportsChunking = record.supportsChunking === true;
    maxAggregatePayloadSize = bridgeMaxPayloadSize;
    if (typeof record.maxAggregatePayloadSize === "number" && record.maxAggregatePayloadSize > 0) {
      maxAggregatePayloadSize = record.maxAggregatePayloadSize;
    }
    serverHotSwapEnabled = record.hotSwapEnabled === true;
    log("Bridge handshake accepted");
  }
  function handleHeartbeatMessage(source) {
    if (source === "extension") return;
    send({ type: "heartbeat", timestamp: Date.now(), source: "extension" });
  }
  function handleMessage(raw) {
    const message = JSON.parse(raw);
    if (isServerActivityMessage(message.type, message.source)) {
      lastServerActivityMs = Date.now();
    }
    switch (message.type) {
      case "hello":
        applyHelloPayload(message);
        return "hello";
      case "heartbeat":
        handleHeartbeatMessage(message.source);
        return "heartbeat";
      case "request":
        void handleRequest(message);
        return "request";
      default:
        return "ignored";
    }
  }
  async function connectToPort(port, runId, showSuccessToast, timeoutMs) {
    const url = buildLocalBridgeWebSocketUrl(port);
    const socketId = `${SOCKET_ID}-${runId}-${port}`;
    return new Promise((resolve) => {
      let settled = false;
      let handle = null;
      let socketGeneration = 0;
      let socketOpened = false;
      let handshakeSent = false;
      let registerFallbackTimer = null;
      const clearRegisterFallback = () => {
        if (!registerFallbackTimer) return;
        runtimeTimers.clearTimeout(registerFallbackTimer);
        registerFallbackTimer = null;
      };
      const finish = (connected) => {
        if (settled) return;
        settled = true;
        clearRegisterFallback();
        runtimeTimers.clearTimeout(timeout);
        resolve(connected);
      };
      const timeout = runtimeTimers.setTimeout(() => {
        clearRegisterFallback();
        if (handshakeSent) {
          recordLocalConnectionDiagnostic({
            phase: "hello-timeout",
            port,
            transport: handle?.type,
            message: `Socket opened on port ${port}, but the MCP bridge hello was not received.`,
            priority: 90
          });
        } else if (handle?.type !== "easyeda-register") {
          recordLocalConnectionDiagnostic({
            phase: "socket-open-timeout",
            port,
            transport: handle?.type,
            message: `The ${handle?.type ?? "WebSocket"} path did not open on port ${port}.`,
            priority: 50
          });
        }
        if (socketHandle === handle) {
          socketHandle = null;
        }
        closeHandle(handle);
        finish(false);
      }, timeoutMs);
      const startSocket = (options = {}) => {
        const generation = ++socketGeneration;
        socketOpened = false;
        handshakeSent = false;
        let attemptHandle = null;
        const isCurrentGeneration = () => runId === connectRunId && generation === socketGeneration;
        const resolvedHandle = () => attemptHandle ?? { type: "easyeda-register", id: socketId };
        try {
          attemptHandle = createSocket(
            socketId,
            url,
            () => {
              if (settled || !isCurrentGeneration()) {
                closeHandle(attemptHandle);
                return;
              }
              socketOpened = true;
              clearRegisterFallback();
              socketHandle = resolvedHandle();
              handshakeSent = true;
              log("Local bridge socket opened; sending handshake", {
                port,
                transport: socketHandle.type
              });
              sendHandshake();
            },
            (data) => {
              if (!isCurrentGeneration()) return;
              try {
                const messageType = handleMessage(data);
                if (messageType === "hello" && !settled) {
                  socketHandle = resolvedHandle();
                  connectedPort = port;
                  connectionState = "connected";
                  reconnectAttempts = 0;
                  manualDisconnectRequested = false;
                  lastLocalConnectionDiagnostic = null;
                  startHeartbeat();
                  if (showSuccessToast) {
                    showToast(`MCP Bridge connected to local server`);
                  }
                  finish(true);
                }
              } catch (error) {
                log("Bridge message error", error);
              }
            },
            () => {
              if (!isCurrentGeneration()) return;
              clearRegisterFallback();
              const currentHandle = resolvedHandle();
              const wasActiveConnection = socketHandle === currentHandle && connectionState === "connected";
              if (!settled) {
                recordLocalConnectionDiagnostic({
                  phase: "socket-closed",
                  port,
                  transport: currentHandle.type,
                  message: `The ${currentHandle.type} path closed before the bridge handshake completed on port ${port}.`,
                  priority: 60
                });
              }
              if (socketHandle === currentHandle) {
                stopHeartbeat();
                socketHandle = null;
                connectedPort = null;
                connectionState = "disconnected";
              }
              if (!settled) {
                finish(false);
              }
              if (wasActiveConnection && !manualDisconnectRequested && runId === connectRunId) {
                scheduleReconnect();
              }
            },
            (error) => {
              if (!isCurrentGeneration()) return;
              clearRegisterFallback();
              const currentHandle = resolvedHandle();
              recordLocalConnectionDiagnostic({
                phase: "socket-error",
                port,
                transport: currentHandle.type,
                message: `The ${currentHandle.type} path failed on port ${port}: ${bridgeErrorMessage(error)}`,
                priority: 70
              });
              if (socketHandle === currentHandle) {
                socketHandle = null;
              }
              closeHandle(currentHandle);
              finish(false);
            },
            options
          );
        } catch (error) {
          log("createSocket threw", error);
          closeHandle(attemptHandle);
          return null;
        }
        handle = attemptHandle;
        if (!attemptHandle) {
          recordLocalConnectionDiagnostic({
            phase: "socket-api-unavailable",
            port,
            message: `No usable EasyEDA or browser WebSocket API was available for port ${port}.`,
            priority: 80
          });
          return null;
        }
        if (!settled && attemptHandle.type === "easyeda-register") {
          const registerHandle = attemptHandle;
          registerFallbackTimer = runtimeTimers.setTimeout(() => {
            if (settled || !isCurrentGeneration() || socketOpened) return;
            registerFallbackTimer = null;
            recordLocalConnectionDiagnostic({
              phase: "register-open-timeout",
              port,
              transport: registerHandle.type,
              message: `SYS_WebSocket.register() accepted port ${port} but did not invoke its open callback; the extension closed that handle and tried a safe alternate socket API.`,
              priority: 85
            });
            closeHandle(registerHandle);
            if (socketHandle === registerHandle) socketHandle = null;
            const fallbackHandle = startSocket({ skipRegister: true });
            if (!fallbackHandle) {
              finish(false);
            }
          }, REGISTER_OPEN_CALLBACK_TIMEOUT_MS);
        }
        return attemptHandle;
      };
      handle = startSocket();
      if (!handle) finish(false);
    });
  }
  async function connectInternal(mode = "manual") {
    const manual = mode === "manual";
    if (connectionState === "connected" && connectedPort !== null) {
      if (manual) {
        showToast(`MCP Bridge already connected to local server`);
      }
      return;
    }
    if (connectionState === "connecting" && activeConnectPromise) {
      if (!manual) return activeConnectPromise;
      connectRunId += 1;
      activeConnectPromise = null;
      closeSocket();
    }
    if (reconnectTimer) {
      runtimeTimers.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    manualDisconnectRequested = false;
    connectionState = "connecting";
    lastLocalConnectionDiagnostic = null;
    const runId = ++connectRunId;
    if (manual) {
      showToast(`MCP Bridge connecting to local server`);
    }
    activeConnectPromise = (async () => {
      try {
        for (const attempt of getLocalBridgeConnectionAttempts(preferredPort)) {
          if (runId !== connectRunId || manualDisconnectRequested) return;
          const connected = await connectToPort(attempt.port, runId, true, attempt.timeoutMs);
          if (connected) {
            preferredPort = attempt.port;
            return;
          }
        }
      } catch (error) {
        log("connect() threw unexpectedly", error);
      } finally {
        if (runId === connectRunId && connectionState === "connecting") {
          connectionState = "disconnected";
          socketHandle = null;
          connectedPort = null;
          const message = `MCP Bridge offline: no local server found${localConnectionDiagnosticSuffix()}`;
          if (manual) {
            showToast(message);
          } else {
            log(message);
          }
          if (!manualDisconnectRequested) {
            scheduleReconnect();
          }
        }
        if (runId === connectRunId) {
          activeConnectPromise = null;
        }
      }
    })();
    return activeConnectPromise;
  }
  function disconnectInternal(notifyUser) {
    if (notifyUser) void updateMenuTitle();
    const wasDisconnected = connectionState === "disconnected" && !socketHandle;
    const wasConnecting = connectionState === "connecting";
    manualDisconnectRequested = true;
    connectRunId += 1;
    activeConnectPromise = null;
    reconnectAttempts = 0;
    if (reconnectTimer) {
      runtimeTimers.clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    stopHeartbeat();
    closeSocket();
    if (!notifyUser) return;
    if (wasDisconnected) {
      showToast("MCP Bridge already disconnected");
    } else if (wasConnecting) {
      showToast("MCP Bridge connection cancelled");
    } else {
      showToast("MCP Bridge disconnected. Auto reconnect is paused until Connect.");
    }
  }
  function disconnectCommandInternal() {
    disconnectInternal(true);
  }
  function showStatusInternal() {
    autoConnectEnabled = loadAutoConnectSetting();
    const autoLabel = autoConnectEnabled ? "Auto-Connect: ON" : "Auto-Connect: OFF";
    if (connectionState === "connected" && connectedPort !== null) {
      showToast(`MCP Bridge connected to local server | ${autoLabel}`);
      return;
    }
    if (connectionState === "connecting") {
      showToast(`MCP Bridge connecting to local server | ${autoLabel}`);
      return;
    }
    if (autoConnectEnabled && !manualDisconnectRequested) {
      showToast(
        `MCP Bridge: waiting for server | ${autoLabel} \u2014 retrying (attempt ${reconnectAttempts + 1})`
      );
      scheduleReconnect();
      return;
    }
    showToast(
      `MCP Bridge disconnected | ${autoLabel} \u2014 click Connect to connect${localConnectionDiagnosticSuffix()}`
    );
  }
  function scheduleReconnect() {
    if (manualDisconnectRequested || reconnectTimer) return;
    reconnectAttempts += 1;
    const delay = reconnectDelayMs(reconnectAttempts);
    reconnectTimer = runtimeTimers.setTimeout(() => {
      reconnectTimer = null;
      if (connectionState === "disconnected") {
        void connectInternal("auto");
      }
    }, delay);
  }
  var autoConnectEnabled = true;
  function getStorage() {
    const globalObj = getGlobal();
    return readPath(globalObj, "sys_Storage");
  }
  function loadAutoConnectSetting() {
    try {
      const storage = getStorage();
      if (storage && typeof storage.getExtensionUserConfig === "function") {
        const val = storage.getExtensionUserConfig("autoConnect");
        if (val !== void 0) return !!val;
      }
    } catch (e) {
      log("sys_Storage.getExtensionUserConfig unavailable", e);
    }
    return true;
  }
  async function saveAutoConnectSetting(value) {
    try {
      const storage = getStorage();
      if (storage && typeof storage.setExtensionUserConfig === "function") {
        const saved = await storage.setExtensionUserConfig("autoConnect", value);
        if (saved === false) {
          log("sys_Storage.setExtensionUserConfig returned false");
        }
      }
    } catch (e) {
      log("sys_Storage.setExtensionUserConfig unavailable", e);
    }
  }
  async function updateMenuTitle() {
    log(`menu state: Auto-Connect=${autoConnectEnabled}`);
  }
  async function setAutoConnectInternal(enabled) {
    autoConnectEnabled = enabled;
    await saveAutoConnectSetting(enabled);
    await updateMenuTitle();
    if (enabled) {
      manualDisconnectRequested = false;
      reconnectAttempts = 0;
      if (connectionState === "disconnected") {
        await connectInternal("auto");
      }
    } else {
      manualDisconnectRequested = true;
      if (reconnectTimer) {
        runtimeTimers.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    }
    showToast(
      enabled ? "Auto-Connect: ON \u2014 will reconnect automatically" : "Auto-Connect: OFF \u2014 use Connect button to connect"
    );
  }
  async function enableAutoConnectInternal() {
    await setAutoConnectInternal(true);
  }
  async function disableAutoConnectInternal() {
    await setAutoConnectInternal(false);
  }
  async function toggleAutoConnectInternal() {
    await setAutoConnectInternal(!loadAutoConnectSetting());
  }
  var activationStarted = false;
  async function handleActivate() {
    autoConnectEnabled = loadAutoConnectSetting();
    if (activationStarted) {
      if (autoConnectEnabled && connectionState === "disconnected" && !activeConnectPromise) {
        void connectInternal("auto");
      }
      return;
    }
    activationStarted = true;
    if (autoConnectEnabled) {
      showToast(`MCP Bridge: Auto-Connect ON \u2014 scanning local server`);
      void connectInternal("auto");
    } else {
      showToast("MCP Bridge: Auto-Connect OFF \u2014 click Connect to connect");
    }
  }
  async function activateInternal(_status, _arg) {
    await handleActivate();
  }
  function deactivateInternal() {
    activationStarted = false;
    disconnectInternal(false);
    remoteRelayClient?.disconnect("disconnected");
    remoteRelayClient = null;
    const globalScope = globalThis;
    const existing = globalScope[PERSISTENT_RUNTIME_KEY];
    if (existing?.deactivate === deactivateInternal) {
      delete globalScope[PERSISTENT_RUNTIME_KEY];
    }
  }
  var PERSISTENT_RUNTIME_KEY = "__easyedaMcpProBridgeRuntime_v8__";
  function getPersistentRuntime() {
    const globalScope = globalThis;
    const existing = globalScope[PERSISTENT_RUNTIME_KEY];
    if (existing) return existing;
    const runtime = {
      activate: activateInternal,
      deactivate: deactivateInternal,
      connect: connectInternal,
      disconnect: disconnectCommandInternal,
      showStatus: showStatusInternal,
      enableAutoConnect: enableAutoConnectInternal,
      disableAutoConnect: disableAutoConnectInternal,
      toggleAutoConnect: toggleAutoConnectInternal,
      connectRemoteRelay: connectRemoteRelayInternal,
      disconnectRemoteRelay: disconnectRemoteRelayInternal,
      showRemoteRelayStatus: showRemoteRelayStatusInternal
    };
    globalScope[PERSISTENT_RUNTIME_KEY] = runtime;
    return runtime;
  }
  var persistentRuntime = getPersistentRuntime();
  async function activate(status, arg) {
    await persistentRuntime.activate(status, arg);
  }
  function deactivate() {
    persistentRuntime.deactivate();
  }
  async function connect(mode = "manual") {
    await persistentRuntime.connect(mode);
  }
  function disconnect() {
    persistentRuntime.disconnect();
  }
  function showStatus() {
    persistentRuntime.showStatus();
  }
  async function enableAutoConnect() {
    await persistentRuntime.enableAutoConnect();
  }
  async function disableAutoConnect() {
    await persistentRuntime.disableAutoConnect();
  }
  async function toggleAutoConnect() {
    await persistentRuntime.toggleAutoConnect();
  }
  function connectRemoteRelay(mode = "hosted", relayUrl, pairingCode) {
    persistentRuntime.connectRemoteRelay(mode, relayUrl, pairingCode);
  }
  function disconnectRemoteRelay() {
    persistentRuntime.disconnectRemoteRelay();
  }
  function showRemoteRelayStatus() {
    persistentRuntime.showRemoteRelayStatus();
  }
  function expose() {
    const api2 = getGlobal();
    if (api2) {
      api2.connect = connect;
      api2.disconnect = disconnect;
      api2.showStatus = showStatus;
      api2.connectRemoteRelay = connectRemoteRelay;
      api2.disconnectRemoteRelay = disconnectRemoteRelay;
      api2.showRemoteRelayStatus = showRemoteRelayStatus;
      api2.enableAutoConnect = enableAutoConnect;
      api2.disableAutoConnect = disableAutoConnect;
      api2.toggleAutoConnect = toggleAutoConnect;
      api2.activate = activate;
      api2.deactivate = deactivate;
    }
    const globalScope = globalThis;
    globalScope.connect = connect;
    globalScope.disconnect = disconnect;
    globalScope.showStatus = showStatus;
    globalScope.connectRemoteRelay = connectRemoteRelay;
    globalScope.disconnectRemoteRelay = disconnectRemoteRelay;
    globalScope.showRemoteRelayStatus = showRemoteRelayStatus;
    globalScope.enableAutoConnect = enableAutoConnect;
    globalScope.disableAutoConnect = disableAutoConnect;
    globalScope.toggleAutoConnect = toggleAutoConnect;
    globalScope.activate = activate;
    globalScope.deactivate = deactivate;
  }
  expose();
  log("Extension script loaded");
  void refreshMethodListHash();
  return __toCommonJS(index_exports);
})();
