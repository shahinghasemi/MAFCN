from metrics import calculateMetric
from torch_geometric.nn import SAGEConv, to_hetero, aggr, ResGatedGraphConv, GATConv, GATv2Conv, TransformerConv, LEConv
import torch
from torch.nn import Linear, ModuleList, Sequential, ReLU, Dropout
from torch.nn.functional import dropout

class GNNEncoder(torch.nn.Module):
    def __init__(self, neurons, layers, aggregator, encoder):
        super().__init__()
        self.layers = layers
        if encoder == 'LEConv':
            self.convs = ModuleList([LEConv((-1, -1), neurons) for i in range(self.layers)])
        elif encoder == 'GATv2Conv':
            self.convs = ModuleList([GATv2Conv((-1, -1), neurons,add_self_loops=False) for i in range(self.layers)])
        elif encoder == 'TransformerConv':
            self.convs = ModuleList([TransformerConv((-1, -1), neurons) for i in range(self.layers)])
        elif encoder == 'GATConv':
            self.convs = ModuleList([GATConv((-1, -1), neurons, add_self_loops=False) for i in range(self.layers)])
        elif encoder == 'ResGatedGraphConv':
            self.convs = ModuleList([ResGatedGraphConv((-1, -1), neurons, ) for i in range(self.layers)])
        elif encoder == 'SAGEConv':
            if aggregator == 'sum':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.SumAggregation()) for i in range(self.layers)])
            elif aggregator == 'var':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.VarAggregation()) for i in range(self.layers)])
            elif aggregator == 'max':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.MaxAggregation()) for i in range(self.layers)])
            elif aggregator == 'mul':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.MulAggregation()) for i in range(self.layers)])
            elif aggregator == 'min':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.MinAggregation()) for i in range(self.layers)])
            elif aggregator == 'power-mean':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.PowerMeanAggregation()) for i in range(self.layers)])
            elif aggregator == 'std':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.StdAggregation()) for i in range(self.layers)])
            elif aggregator == 'softmax':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.SoftmaxAggregation()) for i in range(self.layers)])
            elif aggregator == 'softmax-learn':
                self.convs = ModuleList([SAGEConv((-1, -1), neurons, normalize=True, aggr=aggr.SoftmaxAggregation(learn=True)) for i in range(self.layers)])

    def forward(self, x, edge_index):
        for i, l in enumerate(self.convs):
            if i == self.layers - 1:
                x = self.convs[i](x, edge_index)
            else:
                x = self.convs[i](x, edge_index).relu()
                x = dropout(x, p=0.25)
        return x


class Linears(torch.nn.Module):
    def __init__(self, neurons, aggregator):
        super().__init__()

        if aggregator == 'concatenate':
            self.linear = Sequential(
                Linear(2 * neurons, neurons),
                Dropout(p=0.25),
                ReLU(),
                Linear(neurons, 1)
            )
        elif aggregator == 'mean' or aggregator == 'sum' or aggregator == 'mul':
            self.linear = Sequential(
                Linear(neurons, neurons),
                Dropout(p=0.25),
                ReLU(),
                Linear(neurons, 1)
            )

        self.aggregator = aggregator

    def forward(self, z_dict, edge_label_index):
        row, col = edge_label_index
        if self.aggregator == 'concatenate':
            z = torch.cat([z_dict['drug'][row], z_dict['disease'][col]], dim=-1)

        elif self.aggregator == 'mean':
            drug = z_dict['drug'][row]
            disease = z_dict['disease'][col]
            z = ((drug + disease) /2)

        elif self.aggregator == 'sum':
            drug = z_dict['drug'][row]
            disease = z_dict['disease'][col]
            z = drug + disease 

        elif self.aggregator == 'mul':
            drug = z_dict['drug'][row]
            disease = z_dict['disease'][col]
            z = drug * disease 

        z = self.linear(z)
        return z.view(-1)

class Model(torch.nn.Module):
    def __init__(self, data, neurons, layers, aggregator_lin, aggregator_conv, aggregator_hetero, encoder):
        super().__init__()
        self.encoder = GNNEncoder(neurons, layers, aggregator_conv, encoder)
        self.encoder = to_hetero(self.encoder, data.metadata(), aggr=aggregator_hetero)
        self.linear = Linears(neurons, aggregator_lin)

    def forward(self, x_dict, edge_index_dict, edge_label_index):
        z_dict = self.encoder(x_dict, edge_index_dict)
        return self.linear(z_dict, edge_label_index)


def train(data, model, optimizer, criterion):
    model.train()
    optimizer.zero_grad()
    pred = model(data.x_dict, data.edge_index_dict, data['drug', 'treats', 'disease'].edge_label_index)
    loss = criterion(pred, data['drug', 'treats', 'disease'].edge_label)
    loss.backward()
    optimizer.step()
    return float(loss)

@torch.no_grad()
def test(test_data, model, thresholdPercent):
    model.eval()
    pred = model(test_data.x_dict, test_data.edge_index_dict, test_data['drug','treats', 'disease'].edge_label_index)

    pred = pred.detach().numpy()
    edge_label = test_data['drug','treats', 'disease'].edge_label.detach().numpy()

    edge_label_index = test_data['drug', 'treats', 'disease'].edge_label_index
    metrics = calculateMetric(edge_label, pred, edge_label_index, edge_label, thresholdPercent)
    return metrics

