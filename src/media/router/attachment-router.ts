import * as xlsx from 'xlsx';
import { promises as fsPromises } from 'fs';
import type { LocalAttachment } from '../cache';

export type TaskType = 'WeeklyReport' | 'SupplierCommission' | 'BiddingDocument' | 'ComicNovel' | 'Unknown';

export interface RouteResult {
  taskType: TaskType;
  message: string;
}

export class AttachmentRouter {
  static async route(attachment: LocalAttachment): Promise<RouteResult> {
    const filename = attachment.originalName || attachment.path;

    // 1. WeeklyReport
    if (filename.includes('周报') || filename.includes('Weekly')) {
      return { taskType: 'WeeklyReport', message: '已自动识别为【周报】，派发至绩效考核工作流。' };
    }

    // 2. BiddingDocument
    if (filename.includes('招标书') || filename.includes('Bidding')) {
      return { taskType: 'BiddingDocument', message: '已自动识别为【招标书】，派发至法务合规审核工作流。' };
    }

    // 3. ComicNovel
    if (filename.includes('漫剧') || filename.includes('小说') || filename.includes('Comic') || filename.includes('Novel')) {
      return { taskType: 'ComicNovel', message: '已自动识别为【漫剧小说】，派发至内容审核与IP孵化工作流。' };
    }

    // 4. SupplierCommission (Needs to check excel header)
    if (filename.endsWith('.xlsx') || filename.endsWith('.xls')) {
      try {
        const buffer = await fsPromises.readFile(attachment.path);
        const workbook = xlsx.read(buffer, { type: 'buffer' });
        const firstSheetName = workbook.SheetNames[0];
        if (!firstSheetName) return { taskType: 'Unknown', message: '未知文件类型，请手动选择处理方式。' };
        const worksheet = workbook.Sheets[firstSheetName];
        if (!worksheet) return { taskType: 'Unknown', message: '未知文件类型，请手动选择处理方式。' };

        // Read headers (first row)
        const headers: string[] = [];
        const ref = worksheet['!ref'];
        if (ref) {
            const range = xlsx.utils.decode_range(ref);
            if (range && range.s) {
              for (let C = range.s.c; C <= range.e.c; ++C) {
                const cell = worksheet[xlsx.utils.encode_cell({ c: C, r: range.s.r })];
                if (cell && cell.v) headers.push(String(cell.v));
              }
            }
        } else {
            // fallback: check top level cells
            for(const key of Object.keys(worksheet)) {
                if (key.match(/^[A-Z]+1$/)) {
                    headers.push(String(worksheet[key].v));
                }
            }
        }

        if (headers.some(h => h.includes('供应商') || h.includes('提成') || h.includes('Commission') || h.includes('Supplier'))) {
          return { taskType: 'SupplierCommission', message: '已自动识别为【供应商提成】，派发至财务结算工作流。' };
        }
      } catch (e) {
        console.error('Failed to parse excel file for routing:', e);
      }
    }

    return { taskType: 'Unknown', message: '未知文件类型，请手动选择处理方式。' };
  }
}
