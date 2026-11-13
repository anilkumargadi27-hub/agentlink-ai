import asyncio
import logging
from server.app.core.database import AsyncSessionLocal
from server.app.workers.queue import claim_next_job, execute_job

logger = logging.getLogger("agentlink.worker")

async def worker_loop():
    logger.info("AgentLink background routing & response worker started.")
    while True:
        try:
            async with AsyncSessionLocal() as session:
                job = await claim_next_job(session)
            if job:
                logger.info(f"Claimed job {job.id} (type: {job.type})")
                await execute_job(job)
            else:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in worker loop: {e}")
            await asyncio.sleep(2.0)

if __name__ == "__main__":
    asyncio.run(worker_loop())

