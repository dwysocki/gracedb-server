from django.db import models


# Custom managers for the Pipeline model --------------------------------------
class ProductionPipelineManager(models.Manager):
    """Pipelines which are production search pipelines"""
    def get_queryset(self):
        return super(ProductionPipelineManager, self).get_queryset().filter(
            pipeline_type=self.model.PIPELINE_TYPE_SEARCH_PRODUCTION
        )


class ExternalPipelineManager(models.Manager):
    """Pipelines which correspond to external experiments"""
    def get_queryset(self):
        return super(ExternalPipelineManager, self).get_queryset().filter(
            pipeline_type=self.model.PIPELINE_TYPE_EXTERNAL
        )
