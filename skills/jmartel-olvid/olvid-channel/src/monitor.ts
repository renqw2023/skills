import type {ChannelAccountSnapshot, RuntimeEnv, OpenClawConfig, ReplyPayload, ChannelLogSink} from "openclaw/plugin-sdk";
import { datatypes, OlvidClient } from "@olvid/bot-node";
import { ResolvedOlvidAccount, resolveOlvidAccount } from "./accounts.js";
import { getOlvidRuntime } from "./runtime.js";
import { sendMessageOlvid } from "./send.js";
import { messageIdToString } from "./tools.js";
import { CoreConfig } from "./types.js";
import * as fs from "node:fs";

export type MonitorOlvidOpts = {
  accountId?: string;
  config?: CoreConfig;
  runtime?: RuntimeEnv;
  abortSignal?: AbortSignal;
  logger?: ChannelLogSink;
  statusSink?: (patch: Partial<ChannelAccountSnapshot>) => void;
};

async function deliverOlvidReply(params: {
  payload: { text?: string; mediaUrls?: string[]; mediaUrl?: string; replyToId?: string };
  accountId: string;
  discussionId: bigint;
  statusSink?: (patch: { lastOutboundAt?: number }) => void;
}): Promise<void> {
  const { payload, discussionId, accountId, statusSink } = params;
  const text = payload.text ?? "";
  const mediaList = payload.mediaUrls?.length
    ? payload.mediaUrls
    : payload.mediaUrl
      ? [payload.mediaUrl]
      : [];

  if (!text.trim() && mediaList.length === 0) {
    return;
  }

  const to: string = `olvid:${discussionId}`;

  await sendMessageOlvid(to, text, { accountId, replyTo: payload.replyToId, mediaUrls: mediaList });
  statusSink?.({ lastOutboundAt: Date.now() });
}

class OpenClawBot extends OlvidClient {
  private readonly opts: MonitorOlvidOpts;
  private readonly account: ResolvedOlvidAccount;
  private readonly cfg: CoreConfig;
  private readonly logger?: ChannelLogSink;

  constructor(account: ResolvedOlvidAccount, opts: MonitorOlvidOpts, cfg: CoreConfig) {
    super({ serverUrl: account.daemonUrl, clientKey: account.clientKey });
    this.opts = opts;
    this.account = account;
    this.cfg = cfg;
    this.logger = opts.logger;

    this.onMessageReceived({
      callback: this.onMessageReceivedHandler,
    });
  }

  private async onMessageReceivedHandler(message: datatypes.Message) {
    const runtime = getOlvidRuntime();

    // load metadata
    const discussion: datatypes.Discussion = await this.discussionGet({
      discussionId: message.discussionId,
    });
    const sender: datatypes.Contact | undefined = message.senderId
      ? await this.contactGet({ contactId: message.senderId })
      : undefined;
    const timestamp: number = Number(message.timestamp);
    const isGroup: boolean = await message.isGroupMessage(this);

    // ignore outbound messages (not supposed to happen)
    if (!sender) {
      return;
    }

    // log and update status
    this.logger?.info("message received")
    runtime.channel.activity.record({
      channel: "olvid",
      accountId: this.opts.accountId,
      direction: "inbound",
      at: timestamp,
    });
    this.opts.statusSink?.({ lastInboundAt: Date.now() });

    // download message attachments
    const attachmentsWithPaths: {attachment: datatypes.Attachment, path: string}[] = [];
    if (message.attachmentsCount > 0) {
      fs.mkdirSync("/tmp/olvid-attachments", {recursive: true});
      for await (const attachment of this.attachmentList({filter: new datatypes.AttachmentFilter({messageId: message.id})})) {
        attachmentsWithPaths.push({
          attachment: attachment,
          path: await attachment.save(this, "/tmp/olvid-attachments")
        })
      }
      this.logger?.info(`downloaded ${attachmentsWithPaths.length} attachment(s)`)
    }

    const route = runtime.channel.routing.resolveAgentRoute({
      cfg: this.cfg,
      channel: "olvid",
      accountId: this.account.accountId,
      peer: {
        id: message.discussionId.toString(),
        kind: isGroup ? "group" : "dm",
      },
    });

    const body = runtime.channel.reply.formatInboundEnvelope({
      channel: "olvid",
      from: sender.displayName,
      timestamp: Number(message.timestamp),
      body: message.body,
      sender: { name: sender.displayName, id: sender.id.toString() },
    });

    const ctxPayload = runtime.channel.reply.finalizeInboundContext({
      Body: body,
      RawBody: message.body,
      CommandBody: message.body,
      From: `olvid:${message.discussionId}`,
      To: `olvid:${message.discussionId}`,
      SessionKey: route.sessionKey,
      AccountId: route.accountId,
      ChatType: discussion.isGroupDiscussion() ? "group" : "direct",
      ConversationLabel: discussion.title,
      SenderName: sender ? sender.displayName : "",
      SenderId: sender.id.toString(),
      MessageId: messageIdToString(message.id!),
      Timestamp: message.timestamp,
      Provider: "olvid",
      Surface: "olvid",
      OriginatingChannel: "olvid",
      OriginatingTo: `olvid:${discussion.id}`,
      MediaPath: attachmentsWithPaths.length > 0 ? attachmentsWithPaths[0].path : undefined,
      MediaUrl: attachmentsWithPaths.length > 0 ? attachmentsWithPaths[0].path : undefined,
      MediaType: attachmentsWithPaths.length > 0 ? runtime.media.mediaKindFromMime(attachmentsWithPaths[0].attachment.mimeType) : undefined,
      MediaPaths: attachmentsWithPaths.length > 0 ? attachmentsWithPaths.map(awp => awp.path) : undefined,
      MediaUrls: attachmentsWithPaths.length > 0 ? attachmentsWithPaths.map(awp => awp.path) : undefined,
      MediaTypes: attachmentsWithPaths.length > 0 ? attachmentsWithPaths.map(awp => runtime.media.mediaKindFromMime(awp.attachment.mimeType)) : undefined,
    });

    const storePath = runtime.channel.session.resolveStorePath(
      (this.cfg as OpenClawConfig).session?.store,
      {
        agentId: route.agentId,
      },
    );

    await runtime.channel.session.recordInboundSession({
      storePath,
      sessionKey: ctxPayload.SessionKey ?? route.sessionKey,
      ctx: ctxPayload,
      onRecordError: (err: unknown) => {
        this.logger?.error(`olvid: failed updating session meta: ${String(err)}`);
      },
    });

    await runtime.channel.reply.dispatchReplyWithBufferedBlockDispatcher({
      ctx: ctxPayload,
      cfg: this.cfg,
      dispatcherOptions: {
        deliver: async (payload: ReplyPayload) => {
          if (payload.replyToCurrent) {
            payload.replyToId = messageIdToString(message.id);
          }
          await deliverOlvidReply({
            payload: payload as {
              text?: string;
              mediaUrls?: string[];
              mediaUrl?: string;
              replyToId?: string;
              replyToCurrent?: boolean
            },
            accountId: this.account.accountId,
            discussionId: discussion.id,
            statusSink: this.opts.statusSink,
          });
        },
        onError: (err, info) => {
          this.logger?.error?.(`olvid ${info.kind} reply failed: ${String(err)}`);
        },
      },
    });
  }
}

export async function monitorOlvidProvider(opts: MonitorOlvidOpts = {}): Promise<void> {
  const core = getOlvidRuntime();
  const cfg: CoreConfig = opts.config ?? (core.config.loadConfig() as CoreConfig);
  const account = resolveOlvidAccount({ cfg: cfg, accountId: opts.accountId });
  const logger = core.logging.getChildLogger({
    channel: "olvid",
    accountId: account.accountId,
  });

  if (!account.daemonUrl) {
    throw new Error(`Olvid daemon url not configured for account "${account.accountId}"`);
  }
  if (!account.clientKey) {
    throw new Error(`Olvid client key not configured for account "${account.accountId}"`);
  }

  try {
    const bot = new OpenClawBot(account, opts, cfg);
    opts.statusSink?.({ connected: true, lastConnectedAt: Date.now() });
    await bot.waitForCallbacksEnd();
  } catch (err) {
    logger.error(`olvid: ${err}`);
    opts.statusSink?.({
      lastError: String(err),
      connected: false,
      lastDisconnect: { at: Date.now(), error: String(err) },
    });
  }
}
