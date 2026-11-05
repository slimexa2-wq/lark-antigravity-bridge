import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { AttachmentRouter } from '../../../src/media/router/attachment-router.js';
import type { LocalAttachment } from '../../../src/media/cache.js';
import * as xlsx from 'xlsx';
import * as fs from 'fs';
vi.mock('fs', () => ({ promises: { readFile: vi.fn() } }));


vi.mock('fs');
vi.mock('xlsx', async () => {
    return {
        read: vi.fn(),
        utils: {
            decode_range: vi.fn(),
            encode_cell: vi.fn(),
        }
    };
});

describe('AttachmentRouter', async () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  const createAttachment = (name: string, path: string = '/tmp/test'): LocalAttachment => ({
    originalName: name,
    path,
    absPath: path,
    kind: 'file',
    size: 100,
    mime: 'application/octet-stream',
    hash: 'hash',
    source: 'lark',
    sourceMessageId: 'msg_1',
    sourceFileKey: 'file_1',
    requiredness: 'optional',
    decision: 'accepted'
  });

  it('routes WeeklyReport by filename', async () => {
    const att = createAttachment('2023年10月周报.docx');
    const result = await AttachmentRouter.route(att);
    expect(result.taskType).toBe('WeeklyReport');
  });

  it('routes BiddingDocument by filename', async () => {
    const att = createAttachment('项目招标书_v1.pdf');
    const result = await AttachmentRouter.route(att);
    expect(result.taskType).toBe('BiddingDocument');
  });

  it('routes ComicNovel by filename', async () => {
    const att = createAttachment('漫剧脚本大纲.txt');
    const result = await AttachmentRouter.route(att);
    expect(result.taskType).toBe('ComicNovel');
  });

  it('routes SupplierCommission by reading excel headers', async () => {
    const att = createAttachment('data.xlsx');

    // Mock fs.readFileSync
    (fs.promises.readFile as any).mockResolvedValue(Buffer.from('fake excel data'));

    // Mock xlsx.read
    const mockSheet = {
      '!ref': 'A1:C1',
      'A1': { v: 'ID' },
      'B1': { v: '供应商名称' },
      'C1': { v: '金额' },
    };
    (xlsx.read as any).mockReturnValue({
      SheetNames: ['Sheet1'],
      Sheets: {
        'Sheet1': mockSheet
      }
    });

    (xlsx.utils.decode_range as any).mockReturnValue({s:{c:0, r:0}, e:{c:2, r:0}});
    (xlsx.utils.encode_cell as any).mockImplementation(({c, r}) => {
        if(c === 0 && r === 0) return 'A1';
        if(c === 1 && r === 0) return 'B1';
        if(c === 2 && r === 0) return 'C1';
        return '';
    });

    const result = await AttachmentRouter.route(att);
    expect(result.taskType).toBe('SupplierCommission');
  });

  it('returns Unknown for unrecognized files', async () => {
    const att = createAttachment('random_file.png');
    const result = await AttachmentRouter.route(att);
    expect(result.taskType).toBe('Unknown');
  });
});
